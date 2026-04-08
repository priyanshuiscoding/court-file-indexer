# Court File Indexer

## Local run

1. Copy backend/.env.example to backend/.env if you want local overrides.
2. Make sure Docker is running.
3. Run:

```bash
make up
```

Backend:

- API: [http://localhost:8000](http://localhost:8000)
- Health: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)
- Qdrant: [http://localhost:6333](http://localhost:6333)

## First flow to test

1. Upload a PDF:
   - `POST /api/v1/documents/upload`
2. Start indexing:
   - `POST /api/v1/indexing/{document_id}/start`
3. Fetch rows:
   - `GET /api/v1/indexing/{document_id}/rows`
4. Check ops:
   - `GET /api/v1/ops/status`

## Important

This is a scaffold.
To make it production-ready for High Court scanned PDFs, next upgrades are:

- replace baseline OCR with PaddleOCR image OCR
- add rendered page images and layout-based row extraction
- add Qwen2.5-VL fallback for hard pages
- load official document type/subdocument spreadsheet
- wire Qdrant upsert and retrieval
- add real local RAG chat
- add queue stop/resume/reset controls
- add user auth and audit versioning
