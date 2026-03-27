from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.public_user_schemas import PaginatedPublicUserListings, PublicUserProfileRead
from app.services.public_user_service import PublicUserService

router = APIRouter()


@router.get("/{user_id}", response_model=PublicUserProfileRead)
def get_public_user_profile(user_id: int, db: Session = Depends(get_db)):
    return PublicUserService.get_public_profile(db, user_id)


@router.get("/{user_id}/listings", response_model=PaginatedPublicUserListings)
def get_public_user_listings(
    user_id: int,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return PublicUserService.get_public_user_listings(db, user_id, page=page, page_size=page_size)
