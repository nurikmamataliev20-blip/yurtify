from pydantic import ValidationError
from fastapi import Body, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.router import DualSlashAPIRouter
from app.models.models import User
from app.schemas.promotion_schemas import PaginatedPromotions, PromotionRead, PromotionCreateRequest
from app.services.promotion_service import PromotionService

router = DualSlashAPIRouter()


@router.post("/promotions", response_model=PromotionRead, status_code=status.HTTP_201_CREATED)
def create_promotion(
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    normalized_payload = dict(payload)

    # Backward-compatible field support.
    if "package_id" not in normalized_payload and "promotion_package_id" in normalized_payload:
        normalized_payload["package_id"] = normalized_payload["promotion_package_id"]

    try:
        validated_payload = PromotionCreateRequest.model_validate(normalized_payload)
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.errors())

    try:
        return PromotionService.create_promotion(db, current_user, validated_payload)
    except HTTPException:
        raise
    except TypeError as exc:
        # Prevent timezone comparison edge cases from surfacing as raw 500s.
        if "offset-naive and offset-aware datetimes" in str(exc):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Payment datetime mismatch. Re-initiate payment and try again.",
            )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("/promotions/my", response_model=PaginatedPromotions)
def list_my_promotions(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return PromotionService.list_my_promotions(db, current_user, page=page, page_size=page_size)


@router.get("/promotions/{promotion_id}", response_model=PromotionRead)
def get_promotion(
    promotion_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return PromotionService.get_promotion(db, current_user, promotion_id)


@router.delete("/promotions/{promotion_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_promotion(
    promotion_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    PromotionService.cancel_promotion(db, current_user, promotion_id)
    return None
