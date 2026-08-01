import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.services.student_service import StudentService

router = APIRouter()


@router.get(
    "/",
    status_code=status.HTTP_200_OK,
    summary="Tüm Öğrencileri Listele",
    description="Sisteme kayıtlı tüm öğrencileri getirir.",
)
def get_students(
    limit: int = 100,
    skip: int = 0,
    db: Session = Depends(get_session),
) -> list[dict[str, Any]]:
    """Tüm öğrencileri listeler."""
    service = StudentService(db)
    return service.get_all_students(limit=limit, skip=skip)


@router.get(
    "/{student_id}",
    status_code=status.HTTP_200_OK,
    summary="Öğrenci Detayı",
    description="Öğrencinin temel kimlik ve sınıf bilgilerini getirir.",
)
def get_student(
    student_id: uuid.UUID,
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    """Öğrenci detayını getir."""
    service = StudentService(db)
    student = service.get_student_by_id(student_id)
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Öğrenci bulunamadı.")
    return student


@router.get(
    "/{student_id}/results",
    status_code=status.HTTP_200_OK,
    summary="Öğrencinin Sınav Sonuçları",
    description="Öğrencinin girdiği tüm sınavlardaki ders/konu/kazanım bazlı sonuçlarını (net, doğru, yanlış) listeler.",
)
def get_student_results(
    student_id: uuid.UUID,
    db: Session = Depends(get_session),
) -> list[dict[str, Any]]:
    """Öğrenci sonuçlarını getir."""
    service = StudentService(db)

    # Öğrencinin var olup olmadığını kontrol et (404 için)
    student = service.get_student_by_id(student_id)
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Öğrenci bulunamadı.")

    return service.get_student_results(student_id)
