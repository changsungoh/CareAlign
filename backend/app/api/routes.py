import hashlib
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request

from app.core.config import settings
from app.models.schemas import (
    AnalysisMetadata,
    AnalysisStatus,
    AnalyzeRequest,
    AnalyzeResponse,
    HealthResponse,
    TeachBackRequest,
    TeachBackResponse,
    ValidationStatus,
    VersionResponse,
)
from app.services.conflicts import detect_conflicts
from app.services.extraction import extract_document
from app.services.rate_limit import enforce_rate_limit
from app.services.teachback import evaluate_teachback

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get("/version", response_model=VersionResponse)
def version() -> VersionResponse:
    return VersionResponse(
        app_version=settings.app_version,
        prompt_version=settings.prompt_version,
        rules_version=settings.rules_version,
        dataset_version=settings.dataset_version,
        evaluated_at=datetime.now(UTC),
        demo_mode=settings.demo_mode,
    )


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(
    payload: AnalyzeRequest, request: Request, _: None = Depends(enforce_rate_limit)
) -> AnalyzeResponse:
    del request
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
            await extract_document(document, settings.demo_mode) for document in payload.documents
        ]
    except Exception as error:
        raise HTTPException(
            503,
            "Analysis unavailable. No safety conclusion was produced.",
        ) from error
    instructions = [item for group in instruction_groups for item in group]
    conflicts = detect_conflicts(instructions, document_ids)
    status = AnalysisStatus.NEEDS_REVIEW if conflicts else AnalysisStatus.COMPLETED
    if not instructions or any(
        item.validation_status == ValidationStatus.INSUFFICIENT_INFORMATION for item in instructions
    ):
        status = AnalysisStatus.INSUFFICIENT_INFORMATION
    digest = hashlib.sha256("|".join(document_ids).encode()).hexdigest()[:12]
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
            model_name=settings.llm_model
            if settings.anthropic_api_key
            else "transparent-demo-parser",
            prompt_version=settings.prompt_version,
            rules_version=settings.rules_version,
            dataset_version=settings.dataset_version,
            evaluated_at=datetime.now(UTC),
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
