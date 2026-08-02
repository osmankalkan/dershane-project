import uuid
from typing import Any

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.services.analytics_service import AnalyticsService

router = APIRouter()


@router.get(
    "/students/{student_id}/performance",
    summary="Öğrenci Performans Trendi",
    description="Öğrencinin girdiği tüm sınavlardaki ders bazlı gelişimini (tarih sırasına göre) döndürür.",
)
def get_student_performance(student_id: uuid.UUID, db: Session = Depends(get_session)) -> list[dict[str, Any]]:
    service = AnalyticsService(db)
    return service.get_student_performance_trend(student_id)


@router.get(
    "/institutions/{institution_id}/weak-topics",
    summary="Kurum Geneli En Zayıf Kazanımlar",
    description="Kurumdaki öğrencilerin en çok zorlandığı, başarı oranı en düşük 10 kazanımı döndürür.",
)
def get_institution_weak_topics(institution_id: uuid.UUID, limit: int = 10, db: Session = Depends(get_session)) -> list[dict[str, Any]]:
    service = AnalyticsService(db)
    return service.get_institution_weak_topics(institution_id, limit=limit)


@router.get(
    "/students/{student_id}/ranking",
    status_code=status.HTTP_200_OK,
    summary="Öğrenci Sıralamasını Getir",
    description="Öğrencinin kendi sınıfı ve kurum geneli içindeki sıralamasını döndürür.",
)
def get_student_ranking(
    student_id: uuid.UUID,
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    """Öğrenci sıralama bilgisi."""
    service = AnalyticsService(db)
    return service.get_student_ranking(student_id)


@router.get(
    "/students/at-risk",
    status_code=status.HTTP_200_OK,
    summary="Risk Altındaki Öğrenciler",
    description="Ortalama netine kıyasla son sınavda büyük düşüş yaşayan öğrencileri getirir.",
)
def get_at_risk_students(
    threshold: float = 15.0,
    db: Session = Depends(get_session),
) -> list[dict[str, Any]]:
    """Düşüş trendindeki öğrencileri getir."""
    service = AnalyticsService(db)
    return service.get_at_risk_students(drop_threshold_percent=threshold)
