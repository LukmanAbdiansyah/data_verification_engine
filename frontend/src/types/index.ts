// ── Status types ──
export type Status = 'PASS' | 'PARTIAL' | 'MISSING' | 'INVALID' | 'REVIEW_REQUIRED';
export type EvidenceLevel = 'VERY_HIGH' | 'HIGH' | 'MEDIUM' | 'LOW' | 'INSUFFICIENT';
export type AIAssessmentType = 'SUPPORTED' | 'PARTIALLY_SUPPORTED' | 'INSUFFICIENT_EVIDENCE' | 'CONFLICT' | 'NOT_SUPPORTED';
export type RunStatus = 'pending' | 'scanning' | 'validating' | 'completed' | 'failed' | 'cancelled';

// ── Checklist / Requirement ──
export interface Requirement {
  id: string;
  req_id: string;
  source_row: number;
  progress: string;
  formats: string[];
  validation_note?: string;
}

// ── Checklist Upload Response ──
export interface ChecklistUploadResponse {
  rows: { progress: string; format_str: string }[];
  detected_columns: { progress_column: string | null; format_column: string | null };
  mapping_required: boolean;
  column_options: string[];
  run_id: string;
}

// ── Repository ──
export interface RepositoryFile {
  id: number;
  full_path: string;
  relative_path: string;
  filename: string;
  extension: string;
  size_bytes: number;
  modified_time: string;
  parent_directory: string;
  readable: boolean;
  file_type?: string;
}

export interface ScanProgress {
  files_scanned: number;
  folders_scanned: number;
  current_folder: string;
  elapsed_seconds: number;
  file_type_counts: Record<string, number>;
  status: string;
}

// ── Validation ──
export interface ValidationProgress {
  stage: string;
  processed: number;
  total: number;
  message: string;
  status: string;
  run_id: string;
}

// ── Evidence ──
export interface EvidenceDetail {
  evidence_type: string;
  content: string;
  strength: 'very_strong' | 'strong' | 'supporting';
}

export interface AIAssessmentDetail {
  assessment: AIAssessmentType;
  matched_evidence: string[];
  missing_evidence: string[];
  contradictions: string[];
  reasoning_summary: string;
  latency_ms?: number;
}

// ── Results ──
export interface RequirementResult {
  id: number;
  req_id: string;
  progress: string;
  format_name: string;
  matched_file?: string;
  matched_file_path?: string;
  technical_validation?: Record<string, any>;
  evidence_level?: EvidenceLevel;
  system_status: Status;
  final_status: Status;
  manual_override: boolean;
  reviewer_note?: string;
  evidence_details: EvidenceDetail[];
  ai_assessment?: AIAssessmentDetail;
  candidates?: CandidateInfo[];
}

export interface CandidateInfo {
  filename: string;
  relative_path: string;
  evidence_level: string;
  contradictions: string[];
}

// ── Validation Run / History ──
export interface RunSummary {
  run_id: string;
  date: string;
  checklist: string | null;
  repository: string | null;
  total: number;
  pass_count: number;
  partial_count: number;
  missing_count: number;
  invalid_count: number;
  review_count: number;
  model_name?: string;
  status: RunStatus;
}

// ── Settings ──
export interface Settings {
  theme: 'system' | 'light' | 'dark';
  cache_enabled: boolean;
  segy_validation_enabled: boolean;
  ai_enabled: boolean;
  unsloth_base_url: string;
  api_key: string;
  model_name: string;
  timeout: number;
  max_tokens: number;
  temperature: number;
  max_concurrent_requests: number;
}

// ── Test Connection ──
export interface TestConnectionResult {
  connected: boolean;
  model_ok: boolean;
  latency_ms: number;
  error?: string;
  available_models?: string[];
}

// ── Verification Engine ──
export type VerificationToolName = 'verify_catalog' | 'search_files_by_keywords' | 'verify_keyword_coverage';
export type VerificationItemStatus = 'MATCHED' | 'MISSING' | 'DUPLICATE' | 'EMPTY';
export type CoverageStatus = 'PASS' | 'FAIL';

export interface CatalogResultItem {
  catalog_file?: string;
  row_number: number;
  original_file_name: string | null;
  file_name: string;
  status: VerificationItemStatus;
  file_count: number;
  found_paths: string[];
  metadata_duplicate: boolean;
}

export interface ExtraFileItem {
  file_name: string;
  relative_path: string;
}

export interface CatalogVerificationResult {
  status: string;
  kind: 'catalog';
  tool: string;
  session_id: string;
  configuration: Record<string, any>;
  summary: {
    catalog_files_count?: number;
    catalog_rows: number;
    valid_names: number;
    scanned_files: number;
    matched: number;
    missing: number;
    duplicate: number;
    empty: number;
    extra: number;
    duplicate_metadata_names: number;
  };
  catalog_results: CatalogResultItem[];
  matched_files: CatalogResultItem[];
  missing_files: CatalogResultItem[];
  duplicate_files: CatalogResultItem[];
  empty_metadata: CatalogResultItem[];
  extra_files: ExtraFileItem[];
  warnings: any[];
}

export interface KeywordMatchedFile {
  file_name: string;
  relative_path: string;
  matched_keywords: string[];
}

export interface KeywordSearchResult {
  status: string;
  kind: 'search';
  tool: string;
  session_id: string;
  configuration: Record<string, any>;
  summary: {
    scanned_files: number;
    matched_files: number;
    folders: number;
  };
  matched_files: KeywordMatchedFile[];
  matched_keywords: string[];
  warnings: any[];
}

export interface CoverageFolderResult {
  folder_name: string;
  relative_path: string;
  status: CoverageStatus;
  passed: boolean;
  scanned_files: number;
  matched_file_count: number;
  matched_keywords: string[];
  missing_keywords: string[];
  matched_files: KeywordMatchedFile[];
}

export interface CoverageCheckResult {
  status: string;
  kind: 'coverage';
  tool: string;
  session_id: string;
  configuration: Record<string, any>;
  summary: {
    folders: number;
    pass: number;
    fail: number;
    scanned_files: number;
  };
  folder_results: CoverageFolderResult[];
  warnings: any[];
}
