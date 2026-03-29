from math import ceil
from pathlib import Path
from typing import Optional
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import UPLOADS_DIR
from app.models.models import Listing, User
from app.schemas.user_schemas import UserMeUpdate, UserPublicProfile, PaginatedUserListings


class UserService:
    @staticmethod
    def get_me(current_user: User) -> User:
        return current_user

    @staticmethod
    def update_me(db: Session, current_user: User, user_update: UserMeUpdate) -> User:
        update_data = user_update.model_dump(exclude_unset=True)

        if "phone" in update_data and update_data["phone"] != current_user.phone:
            phone_exists = db.query(User).filter(User.phone == update_data["phone"]).first()
            if phone_exists:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Phone already registered",
                )

        for key, value in update_data.items():
            setattr(current_user, key, value)

        db.commit()
        db.refresh(current_user)
        return current_user

    @staticmethod
    def upload_avatar(db: Session, current_user: User, avatar_file: UploadFile) -> User:
        if not avatar_file.content_type or not avatar_file.content_type.startswith("image/"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only image files are allowed",
            )

        uploads_dir = Path(UPLOADS_DIR)
        uploads_dir.mkdir(parents=True, exist_ok=True)

        ext = Path(avatar_file.filename or "").suffix.lower() or ".jpg"
        filename = f"avatar_{current_user.id}_{uuid4().hex}{ext}"
        file_path = uploads_dir / filename

        content = avatar_file.file.read()
        with open(file_path, "wb") as f:
            f.write(content)

        current_user.profile_image_url = f"/uploads/{filename}"
        db.commit()
        db.refresh(current_user)
        return current_user

    @staticmethod
    def get_public_profile(db: Session, user_id: int) -> UserPublicProfile:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        active_count = (
            db.query(func.count(Listing.id))
            .filter(
                Listing.owner_id == user.id,
                Listing.status == "published",
                Listing.moderation_status == "approved",
                Listing.deleted_at.is_(None),
            )
            .scalar()
            or 0
        )

        return UserPublicProfile(
            id=user.id,
            full_name=user.full_name,
            city=user.city,
            joined_at=user.created_at,
            active_listings_count=active_count,
        )

    @staticmethod
    def get_user_active_listings(
        db: Session,
        user_id: int,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedUserListings:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        base_query = db.query(Listing).filter(
            Listing.owner_id == user_id,
            Listing.status == "published",
            Listing.moderation_status == "approved",
            Listing.deleted_at.is_(None),
        )

        total_items = base_query.count()
        total_pages = ceil(total_items / page_size) if total_items > 0 else 1
        offset = (page - 1) * page_size

        items = (
            base_query.order_by(Listing.created_at.desc())
            .offset(offset)
            .limit(page_size)
            .all()
        )

        return PaginatedUserListings(
            page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=total_pages,
            items=items,
        )
