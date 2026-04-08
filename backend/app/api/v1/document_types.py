from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.services.document_type_service import DocumentTypeService

router = APIRouter(prefix="/document-types", tags=["document-types"])


@router.get("/hierarchy")
def get_document_type_hierarchy():
    service = DocumentTypeService()
    return service.get_hierarchy()


@router.get("/{document_code}")
def get_document_type_children(document_code: str):
    service = DocumentTypeService()
    parent = service.get_parent_by_code(document_code)
    if not parent:
        raise HTTPException(status_code=404, detail="Document type not found")
    return parent
