ALTER TABLE documents ADD COLUMN IF NOT EXISTS case_type VARCHAR(64);
ALTER TABLE documents ADD COLUMN IF NOT EXISTS case_no VARCHAR(64);
ALTER TABLE documents ADD COLUMN IF NOT EXISTS case_year VARCHAR(16);
ALTER TABLE documents ADD COLUMN IF NOT EXISTS case_key VARCHAR(128);
ALTER TABLE documents ADD COLUMN IF NOT EXISTS source_system VARCHAR(64);
ALTER TABLE documents ADD COLUMN IF NOT EXISTS index_json_path TEXT;

CREATE INDEX IF NOT EXISTS ix_documents_case_type ON documents(case_type);
CREATE INDEX IF NOT EXISTS ix_documents_case_no ON documents(case_no);
CREATE INDEX IF NOT EXISTS ix_documents_case_year ON documents(case_year);
CREATE INDEX IF NOT EXISTS ix_documents_case_key ON documents(case_key);
