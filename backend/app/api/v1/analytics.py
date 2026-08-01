import uuid
from typing import Any

from fastapi import APIRouter, Depends
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
