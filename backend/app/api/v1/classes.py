from typing import Any

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.services.institution_service import InstitutionService

router = APIRouter()


@router.get(
    "/",
    status_code=status.HTTP_200_OK,
    summary="Tüm Sınıfları Listele",
    description="Sistemdeki tüm sınıfları getirir.",
)
def get_classes(
    db: Session = Depends(get_session),
) -> list[dict[str, Any]]:
    """Tüm sınıfları listeler."""
    service = InstitutionService(db)
    return service.get_all_classes()
