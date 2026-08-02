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


@router.delete(
    "/{exam_id}",
    status_code=status.HTTP_200_OK,
    summary="Sınavı Sil",
    description="Sınavı ve bu sınava ait tüm öğrenci sonuçlarını (Result) kalıcı olarak siler.",
)
def delete_exam(
    exam_id: Any,
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    """Belirtilen sınavı sil."""
    from fastapi import HTTPException

    service = ExamService(db)
    success = service.delete_exam(exam_id)
    if not success:
        raise HTTPException(status_code=404, detail="Sınav bulunamadı.")
    return {"status": "ok", "message": "Sınav başarıyla silindi."}
