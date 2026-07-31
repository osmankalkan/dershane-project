import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.services.review_service import ReviewService

router = APIRouter()


class ResolveReviewRequest(BaseModel):
    status: str  # "RESOLVED" veya "REJECTED"
    corrected_json: dict[str, Any] | None = None


@router.get(
    "/pending/{institution_id}",
    status_code=status.HTTP_200_OK,
    summary="Bekleyen İncelemeleri Listele",
    description="Bir kuruma ait onay bekleyen tüm PDF işlemlerini getirir.",
)
def get_pending_reviews(
    institution_id: uuid.UUID,
    db: Session = Depends(get_session),
) -> list[dict[str, Any]]:
    """Bekleyen incelemeleri getir."""
    service = ReviewService(db)
    try:
        return service.get_pending_reviews(institution_id)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post(
    "/{review_id}/resolve",
    status_code=status.HTTP_200_OK,
    summary="İncelemeyi Çözümle",
    description="Bekleyen bir incelemeyi onaylar (RESOLVED) veya reddeder (REJECTED).",
)
def resolve_review(
    review_id: uuid.UUID,
    request: ResolveReviewRequest,
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    """İncelemeyi tamamlar."""
    service = ReviewService(db)

    # Faz 0: Sabit sistem kullanıcısı (auth yok)
    # import uuid as _uuid
    # SYSTEM_USER_ID = _uuid.UUID("00000000-0000-0000-0000-00000000000a")
    from app.core.database import SYSTEM_USER_ID

    try:
        return service.resolve_review(
            review_id=review_id,
            resolution_status=request.status,
            resolver_user_id=SYSTEM_USER_ID,
            corrected_json=request.corrected_json,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
