import hashlib
import json
import logging
import time
from datetime import UTC, datetime

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.observability import current_request_id, log_event
from app.models.schemas import (
    AnalysisMetadata,
    AnalysisStatus,
    AnalyzeRequest,
    AnalyzeResponse,
    HealthResponse,
    ReadinessResponse,
    TeachBackRequest,
    TeachBackResponse,
    ValidationStatus,
    VersionResponse,
)
from app.services.conflicts import detect_conflicts
from app.services.extraction import extract_document
from app.services.provider_guard import CircuitOpenError, provider_circuit
from app.services.rate_limit import enforce_analysis_budget, enforce_rate_limit
from app.services.teachback import evaluate_teachback

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get(
    "/readiness",
    response_model=ReadinessResponse,
    responses={503: {"model": ReadinessResponse}},
)
def readiness() -> ReadinessResponse | JSONResponse:
    snapshot = provider_circuit.snapshot()
    ready = settings.provider_mode in {"live", "demo"} and snapshot.state == "closed"
    result = ReadinessResponse(
        status="ready" if ready else "degraded",
        provider_mode=settings.provider_mode,
        provider_circuit=snapshot.state,
        retry_after_seconds=snapshot.retry_after_seconds,
        release_sha=settings.deployment_revision,
    )
    if not ready:
        return JSONResponse(status_code=503, content=result.model_dump(mode="json"))
    return result


@router.get("/version", response_model=VersionResponse)
def version() -> VersionResponse:
    return VersionResponse(
        app_version=settings.app_version,
        prompt_version=settings.prompt_version,
        rules_version=settings.rules_version,
        dataset_version=settings.dataset_version,
        evaluated_at=datetime.now(UTC),
        demo_mode=settings.demo_mode,
        provider_mode=settings.provider_mode,
        release_sha=settings.deployment_revision,
    )


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(
    payload: AnalyzeRequest, request: Request, _: None = Depends(enforce_analysis_budget)
) -> AnalyzeResponse:
    del request
    started = time.perf_counter()
    usage = {"provider_calls": 0, "input_tokens": 0, "output_tokens": 0}

    def record_usage(provider_usage: dict) -> None:
        usage["provider_calls"] += 1
        usage["input_tokens"] += int(provider_usage.get("input_tokens", 0) or 0)
        usage["output_tokens"] += int(provider_usage.get("output_tokens", 0) or 0)

    document_ids = [document.document_id for document in payload.documents]
    if len(document_ids) != len(set(document_ids)):
        raise HTTPException(422, "Document IDs must be unique.")
    dates = [document.document_date for document in payload.documents]
    if len(dates) != len(set(dates)):
        raise HTTPException(422, "Document dates must be unique to establish chronology.")
    if payload.documents != sorted(payload.documents, key=lambda item: item.document_date):
        raise HTTPException(422, "Documents must be ordered from oldest to newest.")
    try:
        instruction_groups = [
            await extract_document(document, settings.demo_mode, record_usage)
            for document in payload.documents
        ]
    except Exception as error:
        # Record only operational metadata. Never log document text, provider
        # response bodies, request headers, or API keys.
        upstream_status = (
            error.response.status_code if isinstance(error, httpx.HTTPStatusError) else None
        )
        log_event(
            "analysis_extraction_failed",
            level=logging.ERROR,
            error_type=type(error).__name__,
            upstream_status=upstream_status,
            provider_circuit=provider_circuit.snapshot().state,
        )
        raise HTTPException(
            503,
            "Analysis temporarily unavailable. No safety conclusion was produced."
            if isinstance(error, CircuitOpenError)
            else "Analysis unavailable. No safety conclusion was produced.",
        ) from error
    instructions = [item for group in instruction_groups for item in group]
    conflicts = detect_conflicts(instructions, document_ids)
    status = AnalysisStatus.NEEDS_REVIEW if conflicts else AnalysisStatus.COMPLETED
    if not instructions or any(
        item.validation_status == ValidationStatus.INSUFFICIENT_INFORMATION for item in instructions
    ):
        status = AnalysisStatus.INSUFFICIENT_INFORMATION
    case_material = json.dumps(
        {
            "documents": [document.model_dump(mode="json") for document in payload.documents],
            "prompt": settings.prompt_version,
            "rules": settings.rules_version,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    digest = hashlib.sha256(case_material.encode()).hexdigest()[:16]
    duration_ms = round((time.perf_counter() - started) * 1000, 2)
    log_event(
        "analysis_completed",
        case_id=f"case-{digest}",
        document_count=len(payload.documents),
        instruction_count=len(instructions),
        conflict_count=len(conflicts),
        status=status.value,
        provider_calls=usage["provider_calls"],
        input_tokens=usage["input_tokens"],
        output_tokens=usage["output_tokens"],
        duration_ms=duration_ms,
    )
    return AnalyzeResponse(
        case_id=f"case-{digest}",
        status=status,
        documents=payload.documents,
        instructions=instructions,
        conflicts=conflicts,
        safety_message=(
            "CareAlign does not determine which instruction is correct. "
            "Confirm every flag with a qualified healthcare professional."
        ),
        metadata=AnalysisMetadata(
            app_version=settings.app_version,
            release_sha=settings.deployment_revision,
            request_id=current_request_id(),
            model_name=settings.llm_model
            if settings.anthropic_api_key
            else "transparent-demo-parser",
            prompt_version=settings.prompt_version,
            rules_version=settings.rules_version,
            dataset_version=settings.dataset_version,
            evaluated_at=datetime.now(UTC),
            provider_calls=usage["provider_calls"],
            input_tokens=usage["input_tokens"],
            output_tokens=usage["output_tokens"],
            analysis_duration_ms=duration_ms,
        ),
        demo_mode=settings.demo_mode,
    )


@router.post("/teach-back", response_model=TeachBackResponse)
def teach_back(
    payload: TeachBackRequest, request: Request, _: None = Depends(enforce_rate_limit)
) -> TeachBackResponse:
    del request
    return evaluate_teachback(
        payload.instructions, set(payload.excluded_instruction_ids), payload.patient_response
    )
