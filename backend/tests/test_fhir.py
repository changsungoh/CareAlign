from fastapi.testclient import TestClient

from app.main import app
from app.services.fhir import FHIRImportError, import_fhir_resource

client = TestClient(app)


def test_imports_r4_bundle_in_chronological_order_with_provenance() -> None:
    bundle = {
        "resourceType": "Bundle",
        "type": "collection",
        "entry": [
            {
                "resource": {
                    "resourceType": "MedicationRequest",
                    "id": "new.rx",
                    "authoredOn": "2026-09-10T09:30:00Z",
                    "medicationCodeableConcept": {"text": "metoprolol tartrate"},
                    "dosageInstruction": [
                        {"text": "Take metoprolol tartrate 25 mg by mouth once a day."}
                    ],
                    "subject": {"display": "Jane Example"},
                }
            },
            {
                "resource": {
                    "resourceType": "MedicationRequest",
                    "id": "old-rx",
                    "authoredOn": "2026-08-20",
                    "medicationCodeableConcept": {
                        "coding": [{"display": "metoprolol tartrate"}]
                    },
                    "dosageInstruction": [
                        {"text": "Take metoprolol tartrate 25 mg by mouth twice a day."}
                    ],
                }
            },
        ],
    }

    body = import_fhir_resource(bundle).model_dump(mode="json")
    assert body["fhir_version"] == "R4"
    assert body["imported_count"] == 2
    assert [item["document_date"] for item in body["documents"]] == [
        "2026-08-20",
        "2026-09-10",
    ]
    assert body["documents"][1]["document_id"] == "fhir-2026-09-10"
    assert "Jane Example" not in str(body)
    assert "dosageInstruction[0].text" in body["provenance"][0]["source_paths"]


def test_resolves_medication_reference_and_renders_structured_dosage() -> None:
    bundle = {
        "resourceType": "Bundle",
        "entry": [
            {
                "resource": {
                    "resourceType": "Medication",
                    "id": "med-1",
                    "code": {"text": "lisinopril"},
                }
            },
            {
                "resource": {
                    "resourceType": "MedicationStatement",
                    "id": "statement-1",
                    "dateAsserted": "2026-08-20",
                    "medicationReference": {"reference": "Medication/med-1"},
                    "dosage": [
                        {
                            "route": {"text": "mouth"},
                            "doseAndRate": [{"doseQuantity": {"value": 10, "unit": "mg"}}],
                            "timing": {"repeat": {"frequency": 1, "period": 1, "periodUnit": "d"}},
                        }
                    ],
                }
            },
        ],
    }

    body = import_fhir_resource(bundle).model_dump(mode="json")
    assert body["ignored_count"] == 1
    assert body["documents"][0]["raw_text"] == "lisinopril 10 mg by mouth once a day."
    assert "medicationReference.reference" in body["provenance"][0]["source_paths"]


def test_skips_unsupported_or_incomplete_entries_without_inventing_data() -> None:
    bundle = {
        "resourceType": "Bundle",
        "entry": [
            {"resource": {"resourceType": "Patient", "id": "patient-1", "name": [{"text": "PHI"}]}},
            {
                "resource": {
                    "resourceType": "MedicationRequest",
                    "id": "missing-date",
                    "medicationCodeableConcept": {"text": "atorvastatin"},
                    "dosageInstruction": [{"text": "Take once daily."}],
                }
            },
            {
                "resource": {
                    "resourceType": "MedicationRequest",
                    "id": "valid",
                    "authoredOn": "2026-09-01",
                    "medicationCodeableConcept": {"text": "atorvastatin"},
                    "dosageInstruction": [{"text": "Take atorvastatin 20 mg once daily."}],
                }
            },
        ],
    }

    response = client.post("/api/fhir/import", json={"resource": bundle})

    assert response.status_code == 200
    body = response.json()
    assert body["imported_count"] == 1
    assert body["ignored_count"] == 2
    assert any("chronology was not inferred" in warning for warning in body["warnings"])
    assert "PHI" not in str(body)


def test_rejects_non_fhir_json_and_empty_supported_set() -> None:
    response = client.post("/api/fhir/import", json={"resource": {"hello": "world"}})
    assert response.status_code == 422
    assert "Expected a FHIR R4" in response.json()["detail"]

    try:
        import_fhir_resource(
            {"resourceType": "Bundle", "entry": [{"resource": {"resourceType": "Patient"}}]}
        )
    except FHIRImportError as error:
        assert "No importable" in str(error)
    else:
        raise AssertionError("Expected an empty supported-resource set to fail")


def test_malformed_or_partial_date_is_not_used_to_invent_chronology() -> None:
    for bad_date in ["2026", "2026-09", "2026-09-01-not-a-datetime"]:
        resource = {
            "resourceType": "MedicationRequest",
            "id": "bad-date",
            "authoredOn": bad_date,
            "medicationCodeableConcept": {"text": "lisinopril"},
            "dosageInstruction": [{"text": "Take lisinopril once daily."}],
        }
        try:
            import_fhir_resource(resource)
        except FHIRImportError as error:
            assert "chronology was not inferred" in str(error)
        else:
            raise AssertionError(f"Expected {bad_date!r} to be rejected")


def test_groups_same_date_medication_resources_into_one_record() -> None:
    bundle = {
        "resourceType": "Bundle",
        "entry": [
            {
                "resource": {
                    "resourceType": "MedicationRequest",
                    "id": f"rx-{index}",
                    "authoredOn": "2026-09-01",
                    "medicationCodeableConcept": {"text": medication},
                    "dosageInstruction": [{"text": f"Take {medication} once daily."}],
                }
            }
            for index, medication in enumerate(["lisinopril", "atorvastatin"], start=1)
        ],
    }

    result = import_fhir_resource(bundle)

    assert result.imported_count == 1
    assert result.documents[0].document_id == "fhir-2026-09-01"
    assert "lisinopril" in result.documents[0].raw_text
    assert "atorvastatin" in result.documents[0].raw_text
    assert len(result.provenance) == 2
    assert any("Grouped 2 medication resources into 1" in warning for warning in result.warnings)
