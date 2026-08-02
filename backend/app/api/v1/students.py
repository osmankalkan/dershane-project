import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.services.student_service import StudentService

router = APIRouter()


@router.get(
    "/",
    status_code=status.HTTP_200_OK,
    summary="Tüm Öğrencileri Listele",
    description="Sisteme kayıtlı tüm öğrencileri getirir. class_id verilirse filtreler.",
)
def get_students(
    class_id: uuid.UUID | None = Query(None, description="Filtrelenecek sınıf ID'si"),
    limit: int = 100,
    skip: int = 0,
    db: Session = Depends(get_session),
) -> list[dict[str, Any]]:
    """Tüm öğrencileri listeler."""
    service = StudentService(db)
    return service.get_all_students(limit=limit, skip=skip, class_id=class_id)


@router.get(
    "/export",
    summary="Öğrenci Listesini İndir",
    description="Tüm öğrencilerin genel başarı durumlarını Excel olarak indirir.",
)
def export_students_list(
    db: Session = Depends(get_session),
):
    from fastapi.responses import Response

    from app.services.excel_report_service import ExcelReportService

    service = ExcelReportService(db)
    excel_bytes = service.generate_student_list_excel()

    return Response(
        content=excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=ogrenciler.xlsx"},
    )


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


@router.get(
    "/{student_id}/export",
    summary="Öğrenci Karne İndir",
    description="Öğrencinin detaylı karnesini Excel formatında indirir.",
)
def export_student_detail(
    student_id: uuid.UUID,
    db: Session = Depends(get_session),
):
    from fastapi.responses import Response

    from app.services.excel_report_service import ExcelReportService

    service = ExcelReportService(db)
    try:
        excel_bytes = service.generate_student_detail_excel(student_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Öğrenci bulunamadı.")

    return Response(
        content=excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=karne_{student_id}.xlsx"},
    )
