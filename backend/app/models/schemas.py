from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ValidationStatus(StrEnum):
    VALIDATED = "validated"
    NEEDS_REVIEW = "needs_review"
    INSUFFICIENT_INFORMATION = "insufficient_information"
    INVALID_OUTPUT = "invalid_output"


class AnalysisStatus(StrEnum):
    COMPLETED = "completed"
    NEEDS_REVIEW = "needs_review"
    INSUFFICIENT_INFORMATION = "insufficient_information"


class ConflictType(StrEnum):
    DOSE = "dose_difference"
    FREQUENCY = "frequency_difference"
    ROUTE = "route_difference"
    ACTION = "action_difference"
    OMISSION = "possible_omission"
    IDENTITY = "identity_uncertain"


class PatternType(StrEnum):
    FIXED = "fixed"
    INTERVAL = "interval"
    PRN = "prn"
    CONDITIONAL = "conditional"
    TAPER = "taper"
    RANGE = "range"
    EVERY_OTHER_DAY = "every_other_day"
    UNSUPPORTED = "unsupported"


class MedicationIdentity(StrictModel):
    raw_name: str = Field(min_length=1, max_length=200)
    normalized_id: str | None = None
    ingredient: str | None = None
    salt: str | None = None
    form: str | None = None
    terminology: str = "curated"
    rxcui: str | None = None
    concept_name: str | None = None
    term_type: str | None = None
    canonical_rxcui: str | None = None
    canonical_name: str | None = None
    canonical_term_type: str | None = None
    match_strategy: str | None = None
    rxnorm_dataset_version: str | None = None
    rxnorm_api_version: str | None = None
    lookup_status: str = "not_requested"


class Dose(StrictModel):
    raw_value: str | None = None
    normalized_value: str | None = None
    raw_unit: str | None = None
    normalized_unit: str | None = None

    @field_validator("raw_value", "normalized_value")
    @classmethod
    def validate_decimal_string(cls, value: str | None) -> str | None:
        if value is None:
            return value
        try:
            Decimal(value)
        except InvalidOperation as error:
            raise ValueError("dose values must be decimal strings") from error
        return value


class Frequency(StrictModel):
    pattern_type: PatternType
    times_per_day: int | None = Field(default=None, ge=1, le=24)
    interval_hours: int | None = Field(default=None, ge=1, le=168)
    minimum_dose: str | None = None
    maximum_dose: str | None = None
    condition: str | None = None
    raw_expression: str = Field(min_length=1, max_length=500)


class Timing(StrictModel):
    values: list[str] = Field(default_factory=list, max_length=10)
    raw_expression: str | None = Field(default=None, max_length=500)


class Route(StrictModel):
    normalized: str | None = None
    raw_expression: str | None = Field(default=None, max_length=200)


class Instruction(StrictModel):
    instruction_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,64}$")
    document_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,64}$")
    medication: MedicationIdentity
    dose: Dose | None = None
    frequency: Frequency | None = None
    timing: Timing | None = None
    route: Route | None = None
    duration: str | None = Field(default=None, max_length=500)
    action: str | None = Field(default=None, max_length=100)
    warning: str | None = Field(default=None, max_length=1000)
    evidence_span: str = Field(min_length=1, max_length=2000)
    evidence_start: int | None = Field(default=None, ge=0)
    evidence_end: int | None = Field(default=None, ge=0)
    validation_status: ValidationStatus = ValidationStatus.NEEDS_REVIEW


class Conflict(StrictModel):
    conflict_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,64}$")
    conflict_type: ConflictType
    medication_name: str
    instruction_ids: list[str] = Field(min_length=1)
    document_ids: list[str] = Field(min_length=1)
    summary: str
    clarification_question: str
    status: ValidationStatus
    confidence: float = Field(ge=0, le=1)
    evidence_spans: list[str] = Field(min_length=1)


class AnalyzeRequest(StrictModel):
    documents: list[CareDocument] = Field(min_length=2, max_length=5)


class AnalyzeResponse(StrictModel):
    case_id: str
    status: AnalysisStatus
    documents: list[CareDocument]
    instructions: list[Instruction]
    conflicts: list[Conflict]
    safety_message: str
    metadata: AnalysisMetadata
    demo_mode: bool = False


class ChecklistItem(StrictModel):
    item_id: str
    instruction_id: str
    category: str
    expected_value: str
    source_evidence: str


class TeachBackRequest(StrictModel):
    instructions: list[Instruction] = Field(min_length=1)
    excluded_instruction_ids: list[str] = Field(default_factory=list)
    patient_response: str = Field(min_length=1, max_length=2000)


class TeachBackFinding(StrictModel):
    item_id: str
    category: str
    result: str
    explanation: str


class TeachBackResponse(StrictModel):
    checklist: list[ChecklistItem]
    findings: list[TeachBackFinding]
    message: str
    needs_human_review: bool
    metadata: AnalysisMetadata


class CareDocument(StrictModel):
    document_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,64}$")
    document_type: str = Field(min_length=1, max_length=100)
    provider: str | None = Field(default=None, max_length=200)
    document_date: date
    raw_text: str = Field(min_length=1, max_length=4000)


class AnalysisMetadata(StrictModel):
    app_version: str
    release_sha: str
    request_id: str
    model_name: str
    prompt_version: str
    rules_version: str
    dataset_version: str
    evaluated_at: datetime
    provider_calls: int = Field(default=0, ge=0)
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    analysis_duration_ms: float = Field(default=0, ge=0)


class HealthResponse(StrictModel):
    status: str


class ReadinessResponse(StrictModel):
    status: str
    provider_mode: str
    provider_circuit: str
    retry_after_seconds: float = Field(ge=0)
    release_sha: str


class VersionResponse(StrictModel):
    app_version: str
    prompt_version: str
    rules_version: str
    dataset_version: str
    evaluated_at: datetime
    demo_mode: bool
    provider_mode: str
    release_sha: str
