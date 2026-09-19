from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union

class ChecklistRow(BaseModel):
    progress: str
    format_str: str

class ColumnMapping(BaseModel):
    progress_column: Optional[str] = None
    format_column: Optional[str] = None

class ChecklistUploadResponse(BaseModel):
    rows: List[ChecklistRow]
    detected_columns: ColumnMapping
    mapping_required: bool
    column_options: List[str]
    run_id: str

class RequirementSchema(BaseModel):
    id: Optional[Union[int, str]] = None
    req_id: str
    source_row: int
    progress: str
    formats: List[str]
    validation_note: Optional[str] = None

class ChecklistConfirmRequest(BaseModel):
    requirements: List[RequirementSchema]

class RepositoryScanRequest(BaseModel):
    path: str
    run_id: Optional[str] = None
    use_cache: bool = True

class ScanProgress(BaseModel):
    files_scanned: int
    folders_scanned: int
    current_folder: str
    elapsed_seconds: float
    file_type_counts: Dict[str, int]
    status: str

class FileInfo(BaseModel):
    id: Optional[int] = None
    full_path: str
    relative_path: str
    filename: str
    extension: str
    size_bytes: int
    modified_time: str
    parent_directory: str
    readable: bool
    file_type: Optional[str] = None

class SegyValidationResult(BaseModel):
    valid_segy: bool
    textual_header_present: bool
    textual_header_encoding: str
    textual_header_lines: List[str]
    binary_header: Dict[str, Any]
    validation_errors: List[str]

class AIResponseSchema(BaseModel):
    assessment: str
    matched_evidence: List[str]
    missing_evidence: List[str]
    contradictions: List[str]
    reasoning_summary: str

class EvidenceDetail(BaseModel):
    evidence_type: str
    content: str
    strength: str

class RequirementResultSchema(BaseModel):
    id: int
    req_id: str
    progress: str
    format_name: str
    matched_file: Optional[str] = None
    matched_file_path: Optional[str] = None
    technical_validation: Optional[Dict[str, Any]] = None
    evidence_level: Optional[str] = None
    system_status: str
    final_status: str
    manual_override: bool
    reviewer_note: Optional[str] = None
    evidence_details: List[EvidenceDetail] = []
    ai_assessment: Optional[AIResponseSchema] = None
    candidates: List[Dict[str, Any]] = []

class ValidationProgress(BaseModel):
    stage: str
    processed: int
    total: int
    message: str
    status: str
    run_id: str

class RunSummary(BaseModel):
    run_id: str
    date: str
    checklist: Optional[str] = None
    repository: Optional[str] = None
    total: int
    pass_count: int
    partial_count: int
    missing_count: int
    invalid_count: int
    review_count: int
    model_name: Optional[str] = None
    status: str

class ManualReviewRequest(BaseModel):
    new_status: str
    reviewer_note: Optional[str] = None

class SettingsSchema(BaseModel):
    theme: str = 'system'
    cache_enabled: bool = True
    segy_validation_enabled: bool = True
    ai_enabled: bool = True
    unsloth_base_url: str = ''
    api_key: str = ''
    model_name: str = ''
    timeout: int = 120
    max_tokens: int = 1000
    temperature: float = 0.0
    max_concurrent_requests: int = 2

class TestConnectionResponse(BaseModel):
    connected: bool
    model_ok: bool
    latency_ms: float
    error: Optional[str] = None
    available_models: List[str] = []

class ExportRequest(BaseModel):
    format: str
