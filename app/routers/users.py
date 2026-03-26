from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.models import User
from app.schemas.user_schemas import PaginatedUserListings, UserMeUpdate, UserPublicProfile, UserRead
from app.services.user_service import UserService

router = APIRouter()


@router.get("/me", response_model=UserRead)
def get_me(current_user: User = Depends(get_current_user)):
    return UserService.get_me(current_user)


@router.put("/me", response_model=UserRead)
def update_me(
    payload: UserMeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return UserService.update_me(db, current_user, payload)


@router.post("/me/avatar", response_model=UserRead)
def upload_avatar(
    avatar: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return UserService.upload_avatar(db, current_user, avatar)


@router.get("/{user_id}", response_model=UserPublicProfile)
def get_public_profile(user_id: int, db: Session = Depends(get_db)):
    return UserService.get_public_profile(db, user_id)


@router.get("/{user_id}/listings", response_model=PaginatedUserListings)
def get_public_user_listings(
    user_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return UserService.get_user_active_listings(db, user_id, page=page, page_size=page_size)
