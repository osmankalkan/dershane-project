import uuid
from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.services.upload_service import UploadResult, UploadService

router = APIRouter()


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    summary="PDF Yükleme ve İşleme Endpoint'i",
    description="Sınav sonuç PDF'ini alır, formatını tanır, verileri çeker ve kaydeder. Faz 0 için senkron (bloklayıcı) çalışır.",
)
def upload_pdf(
    institution_id: uuid.UUID = Form(..., description="PDF'in ait olduğu kurum ID'si"),
    class_id: uuid.UUID = Form(..., description="Öğrencilerin kaydedileceği sınıf ID'si"),
    exam_name: str = Form(..., description="Sınav adı (örn: LGS Deneme 1)"),
    exam_date: date = Form(..., description="Sınav tarihi (YYYY-MM-DD)"),
    file: UploadFile = File(..., description="Sınav sonuçları PDF dosyası"),
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    """PDF dosyasını yükleyip işleme sokar."""

    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Yüklenen dosya PDF formatında olmalıdır.")

    # Dosya boyutunu bellekte okuyup byte olarak servise aktaracağız
    file_bytes = file.file.read()

    # Çok büyük dosyalar için koruma (örneğin 50MB üstü)
    MAX_SIZE_MB = 50
    if len(file_bytes) > MAX_SIZE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=f"Dosya boyutu çok büyük (Maks {MAX_SIZE_MB}MB)."
        )

    service = UploadService(db=db)
    try:
        result: UploadResult = service.upload_pdf(
            file_bytes=file_bytes,
            original_name=file.filename,
            institution_id=institution_id,
            class_id=class_id,
            exam_name=exam_name,
            exam_date=exam_date,
        )

        if result.status == "DUPLICATE":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=result.detail)

        return result.to_dict()

    except HTTPException:
        raise
    except (ValueError, RuntimeError) as ve:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve),
        )
    except Exception as e:
        db.rollback()
        import logging

        logging.getLogger(__name__).error(f"Upload error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"PDF işlenirken bir hata oluştu: {e}",
        )
