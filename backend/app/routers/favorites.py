from fastapi import Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.router import DualSlashAPIRouter
from app.models.models import User
from app.schemas.favorite_schemas import FavoriteRead, PaginatedFavorites
from app.services.favorite_service import FavoriteService

router = DualSlashAPIRouter()


@router.post("/favorites/{listing_id}", response_model=FavoriteRead, status_code=status.HTTP_201_CREATED)
def add_to_favorites(
    listing_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return FavoriteService.add_to_favorites(db, current_user, listing_id)


@router.delete("/favorites/{listing_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_from_favorites(
    listing_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    FavoriteService.remove_from_favorites(db, current_user, listing_id)
    return None


@router.get("/favorites", response_model=PaginatedFavorites)
def list_favorites(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return FavoriteService.list_user_favorites(db, current_user, page=page, page_size=page_size)
