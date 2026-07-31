"""
Review Queue (İnsan Onay Kuyruğu) Servisi.

PDF Engine'in otomatik çözemediği veya eksik çıkardığı (NEEDS_REVIEW) dosyaların
manuel onayı ve düzenlenmesi için gerekli iş mantığını içerir.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.models.raw_file import (
    RawExtraction,
    RawFile,
    RawFileStatus,
    ReviewQueue,
    ReviewQueueStatus,
)

logger = logging.getLogger(__name__)


class ReviewService:
    """İnsan onay süreçlerini yöneten servis."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def get_pending_reviews(self, institution_id: uuid.UUID) -> list[dict[str, Any]]:
        """Bir kuruma ait bekleyen (PENDING) inceleme işlerini getirir.

        API katmanında JSON olarak dönüleceği için liste halinde dict döndürür.
        """
        # ReviewQueue -> RawExtraction -> RawFile üzerinden kurum filtrelemesi
        reviews = (
            self._db.query(ReviewQueue)
            .join(RawExtraction)
            .join(RawFile)
            .filter(
                RawFile.institution_id == institution_id,
                ReviewQueue.status == ReviewQueueStatus.PENDING,
            )
            .order_by(ReviewQueue.created_at.desc())
            .all()
        )

        result = []
        for review in reviews:
            extraction = review.raw_extraction
            raw_file = extraction.raw_file if extraction else None

            result.append(
                {
                    "review_id": str(review.id),
                    "reason": review.reason,
                    "reason_detail": review.reason_detail,
                    "created_at": review.created_at.isoformat(),
                    "file_info": {
                        "original_name": raw_file.original_name if raw_file else "Unknown",
                        "uploaded_at": raw_file.uploaded_at.isoformat() if raw_file else None,
                    },
                    "extraction_info": {
                        "parser_used": extraction.parser_used if extraction else "None",
                        "confidence": extraction.confidence if extraction else 0.0,
                        # Frontend'de göstermek/düzenletmek üzere ham veriyi de dön
                        "raw_json": extraction.raw_json if extraction else {},
                    },
                }
            )

        return result

    def resolve_review(
        self,
        *,
        review_id: uuid.UUID,
        resolution_status: str,
        resolver_user_id: uuid.UUID,
        corrected_json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Kuyruktaki bir incelemeyi sonuçlandırır.

        Eğer insan `RESOLVED` yaparsa ve düzeltilmiş JSON (corrected_json) yollarsa,
        bu JSON parser'ın normalize() fonksiyonundan geçirilerek DB'ye yazılmalıdır.

        Eğer insan `REJECTED` yaparsa, dosya çöp kabul edilir ve işlem kapatılır.
        """
        review = self._db.query(ReviewQueue).filter_by(id=review_id).first()
        if not review:
            raise ValueError(f"Review bulunamadı: {review_id}")

        if review.status != ReviewQueueStatus.PENDING:
            raise ValueError(f"Bu review zaten sonuçlanmış: {review.status}")

        extraction = review.raw_extraction
        raw_file = extraction.raw_file

        if resolution_status == ReviewQueueStatus.REJECTED:
            review.status = ReviewQueueStatus.REJECTED
            review.resolved_by = resolver_user_id

            raw_file.status = RawFileStatus.REJECTED
            self._db.commit()

            logger.info("Review reddedildi: review_id=%s file_id=%s", review.id, raw_file.id)
            return {"status": "REJECTED", "message": "Dosya reddedildi ve kapatıldı."}

        if resolution_status == ReviewQueueStatus.RESOLVED:
            # İnsan JSON'ı düzeltip onayladı
            if not corrected_json:
                raise ValueError("RESOLVED durumu için corrected_json sağlanmalıdır.")

            # TODO: corrected_json'ın normalize ve DB yazma işlemleri.
            # Şu anda doğrudan işlemi sonlandırıp kuyruktan düşürelim (MVP).
            # Tam kapsamlı implementasyon upload_service ile entegre çalışacak.

            review.status = ReviewQueueStatus.RESOLVED
            review.resolved_by = resolver_user_id

            # Ham çıkarma verisini güncellenmiş haliyle ezelim (manuel müdahale)
            extraction.raw_json = corrected_json

            raw_file.status = RawFileStatus.PROCESSED
            self._db.commit()

            logger.info("Review onaylandı: review_id=%s file_id=%s", review.id, raw_file.id)
            return {"status": "RESOLVED", "message": "Düzeltmeler kaydedildi."}

        raise ValueError(f"Geçersiz çözümleme durumu: {resolution_status}")
