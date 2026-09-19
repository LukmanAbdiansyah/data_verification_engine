from datetime import datetime, timezone
import uuid
from typing import List, Optional
from sqlalchemy import String, Integer, Boolean, ForeignKey, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    pass

def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

class ValidationRun(Base):
    __tablename__ = 'validation_runs'
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    checklist_source: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    checklist_filename: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    repository_root: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    scan_timestamp: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    app_version: Mapped[str] = mapped_column(String, default='1.0.0')
    model_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    ai_endpoint: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, default='pending')
    total_requirements: Mapped[int] = mapped_column(Integer, default=0)
    pass_count: Mapped[int] = mapped_column(Integer, default=0)
    partial_count: Mapped[int] = mapped_column(Integer, default=0)
    missing_count: Mapped[int] = mapped_column(Integer, default=0)
    invalid_count: Mapped[int] = mapped_column(Integer, default=0)
    review_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[str] = mapped_column(String, default=_utcnow_iso)
    updated_at: Mapped[Optional[str]] = mapped_column(String, nullable=True)

class Requirement(Base):
    __tablename__ = 'requirements'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String, ForeignKey('validation_runs.id'))
    req_id: Mapped[str] = mapped_column(String)
    source_row: Mapped[int] = mapped_column(Integer)
    progress: Mapped[str] = mapped_column(Text)
    formats_json: Mapped[str] = mapped_column(Text)
    validation_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

class RepositoryFile(Base):
    __tablename__ = 'repository_files'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String, ForeignKey('validation_runs.id'))
    full_path: Mapped[str] = mapped_column(Text)
    relative_path: Mapped[str] = mapped_column(Text)
    filename: Mapped[str] = mapped_column(Text)
    extension: Mapped[str] = mapped_column(String)
    size_bytes: Mapped[int] = mapped_column(Integer)
    modified_time: Mapped[str] = mapped_column(String)
    parent_directory: Mapped[str] = mapped_column(Text)
    readable: Mapped[bool] = mapped_column(Boolean, default=True)
    file_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)

class RequirementResult(Base):
    __tablename__ = 'requirement_results'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String, ForeignKey('validation_runs.id'))
    requirement_id: Mapped[int] = mapped_column(Integer, ForeignKey('requirements.id'))
    format_name: Mapped[str] = mapped_column(String)
    matched_file_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('repository_files.id'), nullable=True)
    technical_validation_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    evidence_level: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    system_status: Mapped[str] = mapped_column(String)
    final_status: Mapped[str] = mapped_column(String)
    manual_override: Mapped[bool] = mapped_column(Boolean, default=False)
    reviewer_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    review_timestamp: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    evidence_data_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ai_assessment_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

class CandidateEvidence(Base):
    __tablename__ = 'candidate_evidence'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    result_id: Mapped[int] = mapped_column(Integer, ForeignKey('requirement_results.id'))
    file_id: Mapped[int] = mapped_column(Integer, ForeignKey('repository_files.id'))
    evidence_type: Mapped[str] = mapped_column(String)
    evidence_data_json: Mapped[str] = mapped_column(Text)
    strength: Mapped[str] = mapped_column(String)

class AIAssessment(Base):
    __tablename__ = 'ai_assessments'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    result_id: Mapped[int] = mapped_column(Integer, ForeignKey('requirement_results.id'))
    request_payload_hash: Mapped[str] = mapped_column(String)
    assessment: Mapped[str] = mapped_column(Text)
    matched_evidence_json: Mapped[str] = mapped_column(Text)
    missing_evidence_json: Mapped[str] = mapped_column(Text)
    contradictions_json: Mapped[str] = mapped_column(Text)
    reasoning_summary: Mapped[str] = mapped_column(Text)
    model_name: Mapped[str] = mapped_column(String)
    latency_ms: Mapped[int] = mapped_column(Integer)
    cached: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[str] = mapped_column(String, default=_utcnow_iso)

class ManualReview(Base):
    __tablename__ = 'manual_reviews'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    result_id: Mapped[int] = mapped_column(Integer, ForeignKey('requirement_results.id'))
    previous_status: Mapped[str] = mapped_column(String)
    new_status: Mapped[str] = mapped_column(String)
    reviewer_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    timestamp: Mapped[str] = mapped_column(String, default=_utcnow_iso)

class SettingsMetadata(Base):
    __tablename__ = 'settings_metadata'
    key: Mapped[str] = mapped_column(String, primary_key=True)
    value: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[str] = mapped_column(String, default=_utcnow_iso)
