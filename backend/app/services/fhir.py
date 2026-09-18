from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from typing import Any

from app.models.schemas import CareDocument, FHIRImportResponse, FHIRProvenance

SUPPORTED_RESOURCES = {"MedicationRequest", "MedicationStatement"}
MAX_DOCUMENTS = 5


class FHIRImportError(ValueError):
    """The supplied JSON is not a supported FHIR R4 resource."""


@dataclass(frozen=True)
class Candidate:
    document: CareDocument
    provenance: FHIRProvenance


def import_fhir_resource(payload: dict[str, Any]) -> FHIRImportResponse:
    entries = _entries(payload)
    references = _reference_index(entries)
    warnings: list[str] = []
    candidates: list[Candidate] = []

    for entry_index, resource in entries:
        resource_type = resource.get("resourceType")
        if resource_type not in SUPPORTED_RESOURCES:
            continue
        try:
            candidates.append(_to_candidate(resource, entry_index, references))
        except FHIRImportError as error:
            warnings.append(f"{resource_type} at entry {entry_index}: {error}")

    candidates.sort(key=lambda item: (item.document.document_date, item.document.document_id))
    dated_groups: dict[date, list[Candidate]] = {}
    for candidate in candidates:
        dated_groups.setdefault(candidate.document.document_date, []).append(candidate)

    selected_dates = sorted(dated_groups)[:MAX_DOCUMENTS]
    if len(dated_groups) > MAX_DOCUMENTS:
        excluded_resources = sum(
            len(dated_groups[group_date]) for group_date in sorted(dated_groups)[MAX_DOCUMENTS:]
        )
        warnings.append(
            f"Only the earliest {MAX_DOCUMENTS} dated records were imported; "
            f"{excluded_resources} resources from later dates were not imported."
        )
    selected_candidates = [
        item for group_date in selected_dates for item in dated_groups[group_date]
    ]
    documents, provenance = _group_by_date(selected_dates, dated_groups, warnings)
    if len(selected_candidates) > len(selected_dates):
        warnings.append(
            f"Grouped {len(selected_candidates)} medication resources into "
            f"{len(documents)} dated care records."
        )

    if not documents:
        detail = f" First issue: {warnings[0]}" if warnings else ""
        raise FHIRImportError(
            "No importable MedicationRequest or MedicationStatement resources were found."
            + detail
        )

    return FHIRImportResponse(
        fhir_version="R4",
        documents=documents,
        provenance=provenance,
        warnings=warnings,
        source_resource_count=len(entries),
        imported_count=len(documents),
        ignored_count=max(0, len(entries) - len(provenance)),
    )


def _group_by_date(
    selected_dates: list[date],
    dated_groups: dict[date, list[Candidate]],
    warnings: list[str],
) -> tuple[list[CareDocument], list[FHIRProvenance]]:
    documents: list[CareDocument] = []
    provenance: list[FHIRProvenance] = []
    for group_date in selected_dates:
        group = dated_groups[group_date]
        document_id = f"fhir-{group_date.isoformat()}"
        lines: list[str] = []
        included: list[Candidate] = []
        for candidate in group:
            next_text = "\n".join([*lines, candidate.document.raw_text])
            if len(next_text) > 4000:
                warnings.append(
                    f"{candidate.provenance.resource_type} at entry "
                    f"{candidate.provenance.bundle_entry_index} exceeded the 4,000-character "
                    f"record limit for {group_date}; it was not imported."
                )
                continue
            lines.append(candidate.document.raw_text)
            included.append(candidate)
        if not included:
            continue
        resource_types = {item.provenance.resource_type for item in included}
        document_type = (
            f"FHIR {next(iter(resource_types))} record"
            if len(resource_types) == 1
            else "FHIR medication record"
        )
        documents.append(
            CareDocument(
                document_id=document_id,
                document_type=document_type,
                document_date=group_date,
                raw_text="\n".join(lines),
            )
        )
        provenance.extend(
            item.provenance.model_copy(update={"document_id": document_id}) for item in included
        )
    return documents, provenance


def _entries(payload: dict[str, Any]) -> list[tuple[int, dict[str, Any]]]:
    resource_type = payload.get("resourceType")
    if resource_type == "Bundle":
        raw_entries = payload.get("entry")
        if not isinstance(raw_entries, list):
            raise FHIRImportError("FHIR Bundle.entry must be an array.")
        entries: list[tuple[int, dict[str, Any]]] = []
        for index, entry in enumerate(raw_entries):
            if isinstance(entry, dict) and isinstance(entry.get("resource"), dict):
                entries.append((index, entry["resource"]))
        return entries
    if resource_type in SUPPORTED_RESOURCES:
        return [(0, payload)]
    raise FHIRImportError(
        "Expected a FHIR R4 Bundle, MedicationRequest, or MedicationStatement resource."
    )


def _reference_index(entries: list[tuple[int, dict[str, Any]]]) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for _, resource in entries:
        resource_type = resource.get("resourceType")
        resource_id = resource.get("id")
        if isinstance(resource_type, str) and isinstance(resource_id, str):
            index[f"{resource_type}/{resource_id}"] = resource
            index[resource_id] = resource
    return index


def _to_candidate(
    resource: dict[str, Any],
    entry_index: int,
    references: dict[str, dict[str, Any]],
) -> Candidate:
    resource_type = str(resource["resourceType"])
    resource_id = resource.get("id") if isinstance(resource.get("id"), str) else None
    medication, medication_paths = _medication_name(resource, references)
    document_date, date_path = _resource_date(resource)
    raw_text, dosage_paths = _render_instructions(resource, medication)
    document_id = _document_id(resource_type, resource_id, entry_index)
    return Candidate(
        document=CareDocument(
            document_id=document_id,
            document_type=f"FHIR {resource_type}",
            document_date=document_date,
            raw_text=raw_text,
        ),
        provenance=FHIRProvenance(
            document_id=document_id,
            resource_type=resource_type,
            resource_id=resource_id,
            bundle_entry_index=entry_index,
            source_paths=[*medication_paths, date_path, *dosage_paths],
        ),
    )


def _medication_name(
    resource: dict[str, Any], references: dict[str, dict[str, Any]]
) -> tuple[str, list[str]]:
    concept = resource.get("medicationCodeableConcept")
    if isinstance(concept, dict):
        name = _codeable_concept_text(concept)
        if name:
            return name, ["medicationCodeableConcept"]

    reference = resource.get("medicationReference")
    if isinstance(reference, dict):
        display = reference.get("display")
        if isinstance(display, str) and display.strip():
            return _bounded_medication_name(display), ["medicationReference.display"]
        reference_value = reference.get("reference")
        if isinstance(reference_value, str):
            target = references.get(reference_value) or references.get(
                reference_value.rsplit("/", 1)[-1]
            )
            if target and target.get("resourceType") == "Medication":
                code = target.get("code")
                if isinstance(code, dict):
                    name = _codeable_concept_text(code)
                    if name:
                        return name, ["medicationReference.reference", f"{reference_value}.code"]

    raise FHIRImportError("medication has no readable text or display; no identity was inferred.")


def _codeable_concept_text(concept: dict[str, Any]) -> str | None:
    text = concept.get("text")
    if isinstance(text, str) and text.strip():
        return _bounded_medication_name(text)
    coding = concept.get("coding")
    if isinstance(coding, list):
        for item in coding:
            if isinstance(item, dict):
                display = item.get("display")
                if isinstance(display, str) and display.strip():
                    return _bounded_medication_name(display)
    return None


def _bounded_medication_name(value: str) -> str:
    cleaned = value.strip()
    if len(cleaned) > 200:
        raise FHIRImportError("medication display exceeds the 200-character safety limit.")
    return cleaned


def _resource_date(resource: dict[str, Any]) -> tuple[date, str]:
    resource_type = resource["resourceType"]
    paths = (
        ["authoredOn", "meta.lastUpdated"]
        if resource_type == "MedicationRequest"
        else ["dateAsserted", "effectiveDateTime", "effectivePeriod.start", "meta.lastUpdated"]
    )
    for path in paths:
        value = _get_path(resource, path)
        if not isinstance(value, str):
            continue
        if not re.match(r"^\d{4}-\d{2}-\d{2}(?:$|T)", value):
            continue
        try:
            # A FHIR date may be partial. CareAlign refuses to invent missing month/day values.
            return date.fromisoformat(value[:10]), path
        except ValueError:
            continue
    raise FHIRImportError(
        "no complete YYYY-MM-DD source date was present; chronology was not inferred."
    )


def _render_instructions(resource: dict[str, Any], medication: str) -> tuple[str, list[str]]:
    dosage_key = (
        "dosageInstruction" if resource["resourceType"] == "MedicationRequest" else "dosage"
    )
    dosages = resource.get(dosage_key)
    if not isinstance(dosages, list) or not dosages:
        return (
            f"{medication}. The FHIR resource contains no readable dosage instruction.",
            [dosage_key],
        )

    lines: list[str] = []
    paths: list[str] = []
    for index, dosage in enumerate(dosages):
        if not isinstance(dosage, dict):
            continue
        text = dosage.get("text")
        if isinstance(text, str) and text.strip():
            clean = text.strip()
            line = clean if medication.casefold() in clean.casefold() else f"{medication}: {clean}"
            lines.append(line)
            paths.append(f"{dosage_key}[{index}].text")
            continue
        rendered, used = _render_structured_dosage(dosage, medication, f"{dosage_key}[{index}]")
        lines.append(rendered)
        paths.extend(used)

    if not lines:
        return (
            f"{medication}. The FHIR resource contains no readable dosage instruction.",
            [dosage_key],
        )
    rendered = "\n".join(lines)
    if len(rendered) > 4000:
        raise FHIRImportError("dosage text exceeds the 4,000-character record limit.")
    return rendered, paths


def _render_structured_dosage(
    dosage: dict[str, Any], medication: str, base_path: str
) -> tuple[str, list[str]]:
    pieces = [medication]
    used: list[str] = []
    dose_and_rate = dosage.get("doseAndRate")
    if isinstance(dose_and_rate, list) and dose_and_rate and isinstance(dose_and_rate[0], dict):
        quantity = dose_and_rate[0].get("doseQuantity")
        if isinstance(quantity, dict):
            value = quantity.get("value")
            unit = quantity.get("unit") or quantity.get("code")
            if isinstance(value, (int, float)) and isinstance(unit, str):
                rendered_value = f"{value:g}" if isinstance(value, float) else str(value)
                pieces.append(f"{rendered_value} {unit}")
                used.append(f"{base_path}.doseAndRate[0].doseQuantity")

    route = dosage.get("route")
    if isinstance(route, dict):
        route_text = _codeable_concept_text(route)
        if route_text:
            pieces.append(f"by {route_text}")
            used.append(f"{base_path}.route")

    repeat = _get_path(dosage, "timing.repeat")
    if isinstance(repeat, dict):
        frequency = repeat.get("frequency")
        period = repeat.get("period")
        unit = repeat.get("periodUnit")
        expression = _frequency_text(frequency, period, unit)
        if expression:
            pieces.append(expression)
            used.append(f"{base_path}.timing.repeat")

    if not used:
        return (
            f"{medication}. A structured dosage was present but could not be rendered "
            "without inference.",
            [base_path],
        )
    return " ".join(pieces) + ".", used


def _frequency_text(frequency: Any, period: Any, unit: Any) -> str | None:
    if (
        not isinstance(frequency, int)
        or not isinstance(period, (int, float))
        or not isinstance(unit, str)
    ):
        return None
    if period == 1 and unit in {"d", "day"}:
        return {1: "once a day", 2: "twice a day"}.get(frequency, f"{frequency} times a day")
    rendered_period = f"{period:g}" if isinstance(period, float) else str(period)
    return f"{frequency} time(s) every {rendered_period} {unit}"


def _get_path(resource: dict[str, Any], path: str) -> Any:
    value: Any = resource
    for part in path.split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    return value


def _document_id(resource_type: str, resource_id: str | None, entry_index: int) -> str:
    stem = resource_id or str(entry_index + 1)
    safe = re.sub(r"[^A-Za-z0-9_-]", "-", stem).strip("-") or str(entry_index + 1)
    prefix = "fhir-mr" if resource_type == "MedicationRequest" else "fhir-ms"
    return f"{prefix}-{entry_index + 1}-{safe}"[:64]
