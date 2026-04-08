from fastapi import APIRouter
from app.schemas.mapping import MappingLabelOut
from app.services.mapping_sheet_service import MappingSheetService

router = APIRouter(prefix="/mapping", tags=["mapping"])
service = MappingSheetService()


@router.get("/labels", response_model=list[MappingLabelOut])
def get_mapping_labels():
    labels = service.get_labels()
    return [
        MappingLabelOut(
            document_type=item["document_type"],
            sub_document_type=item["sub_document_type"],
            keywords_en=item.get("keywords_en"),
            keywords_hi=item.get("keywords_hi"),
            regex_rules=item.get("regex_rules"),
            priority=item.get("priority", 100),
        )
        for item in labels
    ]
