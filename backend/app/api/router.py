from fastapi import APIRouter
from app.api.v1.batches import router as batches_router
from app.api.v1.chat import router as chat_router
from app.api.v1.documents import router as documents_router
from app.api.v1.document_types import router as document_types_router
from app.api.v1.health import router as health_router
from app.api.v1.indexing import router as indexing_router
from app.api.v1.mapping import router as mapping_router
from app.api.v1.ops import router as ops_router
from app.api.v1.pages import router as pages_router
from app.api.v1.runtime_ops import router as runtime_router
from app.api.v1.retries import router as retries_router
from app.api.v1.integrations import router as integrations_router
from app.api.v1.ws import router as ws_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(documents_router)
api_router.include_router(batches_router)
api_router.include_router(indexing_router)
api_router.include_router(ops_router)
api_router.include_router(pages_router)
api_router.include_router(runtime_router)
api_router.include_router(retries_router)
api_router.include_router(mapping_router)
api_router.include_router(document_types_router)
api_router.include_router(chat_router)
api_router.include_router(integrations_router)
api_router.include_router(ws_router)
