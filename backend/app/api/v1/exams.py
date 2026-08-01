from typing import Any

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.services.exam_service import ExamService

router = APIRouter()


@router.get(
    "/",
    status_code=status.HTTP_200_OK,
    summary="Tüm Sınavları Listele",
    description="Sisteme yüklenen tüm sınavları getirir.",
)
def get_exams(
    limit: int = 100,
    skip: int = 0,
    db: Session = Depends(get_session),
) -> list[dict[str, Any]]:
    """Sınav listesini getir."""
    service = ExamService(db)
    return service.get_all_exams(limit=limit, skip=skip)
