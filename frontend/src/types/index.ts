export type DocumentItem = {
  id: number;
  cnr_number?: string | null;
  case_title?: string | null;
  file_name: string;
  page_count: number;
  status: string;
  current_step: string;
  is_vectorized: boolean;
  chat_ready: boolean;
  batch_no?: string | null;
  created_at: string;
};

export type IndexRow = {
  id: number;
  document_id: number;
  row_no?: number | null;
  source_page_no?: number | null;
  description_raw: string;
  description_normalized?: string | null;
  annexure_no?: string | null;
  page_from?: number | null;
  page_to?: number | null;
  total_pages?: number | null;
  mapped_document_type?: string | null;
  mapped_sub_document_type?: string | null;
  receiving_date?: string | null;
  extraction_confidence: number;
  verification_confidence: number;
  status: string;
  generated_from_content?: boolean;
  created_at: string;
};

export type DocumentPage = {
  page_no: number;
  image_path?: string | null;
  ocr_text?: string | null;
  ocr_confidence?: number;
  is_candidate_index_page?: boolean;
  candidate_score?: number;
};

export type OpsStatus = {
  indexed_count: number;
  vectorized_count: number;
  pending_queue_count: number;
  review_queue_count: number;
  failed_count: number;
};

export type OpsQueueItem = {
  id: number;
  queue_name: string;
  document_id: number;
  document_name?: string | null;
  document_status?: string | null;
  status: string;
  priority: number;
  attempts: number;
  task_id?: string | null;
  heartbeat_at?: string | null;
  stale_seconds?: number | null;
  is_stuck?: boolean;
  created_at: string;
};

export type QueueActionResult = {
  ok: boolean;
  message: string;
  affected: number;
};

export type ChatAskResponse = {
  answer: string;
  citations: Array<{
    page_no: number;
    score: number;
    snippet: string;
  }>;
};

export type ChatMessage = {
  id: number;
  document_id: number;
  role: string;
  content: string;
  citations_json?: string | null;
  created_at: string;
};

export type HighCourtImportJob = {
  id: number;
  source_system: string;
  external_row_id?: string | null;
  batch_no: string;
  fil_no?: string | null;
  source_pdf_path?: string | null;
  document_id?: number | null;
  status: string;
  error_message?: string | null;
  import_attempts: number;
  last_attempt_at?: string | null;
  imported_at?: string | null;
  created_at: string;
  updated_at: string;
};

export type HighCourtJobListResponse = {
  ok: boolean;
  count: number;
  jobs: HighCourtImportJob[];
};

export type HighCourtSchedulerStatus = {
  enabled: boolean;
  import_every_seconds: number;
  import_limit: number;
  sync_status_every_seconds: number;
  mark_complete_enabled: boolean;
  mark_complete_every_seconds: number;
  mark_complete_limit: number;
  external_mysql_mark_complete_enabled: boolean;
};

export type HighCourtImportItemResult = {
  external_row_id?: number | string | null;
  batch_no?: string | null;
  fil_no?: string | null;
  pdf_path?: string | null;
  status: string;
  document_id?: number | null;
  error?: string | null;
};

export type HighCourtResultResponse = {
  ok: boolean;
  status?: string;
  message?: string;
  error?: string;
  batch_no?: string;
  document_id?: number | null;
  json_path?: string;
  index_json?: unknown;
};
