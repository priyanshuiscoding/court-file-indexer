CREATE TABLE IF NOT EXISTS high_court_import_jobs (
    id SERIAL PRIMARY KEY,
    source_system VARCHAR(128) DEFAULT 'high_court_mysql',
    external_row_id VARCHAR(128),
    batch_no VARCHAR(128) NOT NULL,
    fil_no VARCHAR(128),
    source_pdf_path TEXT,
    document_id INTEGER REFERENCES documents(id) ON DELETE SET NULL,
    status VARCHAR(64) DEFAULT 'DISCOVERED',
    error_message TEXT,
    import_attempts INTEGER DEFAULT 0,
    last_attempt_at TIMESTAMP NULL,
    imported_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_hc_import_jobs_source_system ON high_court_import_jobs(source_system);
CREATE INDEX IF NOT EXISTS ix_hc_import_jobs_external_row_id ON high_court_import_jobs(external_row_id);
CREATE INDEX IF NOT EXISTS ix_hc_import_jobs_batch_no ON high_court_import_jobs(batch_no);
CREATE INDEX IF NOT EXISTS ix_hc_import_jobs_fil_no ON high_court_import_jobs(fil_no);
CREATE INDEX IF NOT EXISTS ix_hc_import_jobs_document_id ON high_court_import_jobs(document_id);
CREATE INDEX IF NOT EXISTS ix_hc_import_jobs_status ON high_court_import_jobs(status);

CREATE UNIQUE INDEX IF NOT EXISTS ux_hc_import_jobs_batch_no ON high_court_import_jobs(batch_no);
