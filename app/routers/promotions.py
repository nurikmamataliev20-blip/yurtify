from fastapi import Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.router import DualSlashAPIRouter
from app.models.models import User
from app.schemas.promotion_schemas import PaginatedPromotions, PromotionRead
from app.services.promotion_service import PromotionService

router = DualSlashAPIRouter()


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
