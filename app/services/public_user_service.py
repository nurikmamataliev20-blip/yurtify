from math import ceil

from fastapi import HTTPException, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.models.models import Listing, User
from app.schemas.public_user_schemas import (
    PaginatedPublicUserListings,
    PublicUserProfileRead,
    PublicUserSearchResponse,
)


class PublicUserService:
    @staticmethod
    def _get_active_public_user(db: Session, user_id: int) -> User:
        user = db.query(User).filter(User.id == user_id).first()
        if not user or user.account_status in {"suspended", "deleted"}:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return user

    @staticmethod
    def get_public_profile(db: Session, user_id: int) -> PublicUserProfileRead:
        user = PublicUserService._get_active_public_user(db, user_id)

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

        return PublicUserProfileRead(
            id=user.id,
            full_name=user.full_name,
            profile_image_url=user.profile_image_url,
            bio=user.bio,
            city=user.city,
            created_at=user.created_at,
            active_listings_count=active_count,
        )

    @staticmethod
    def get_public_user_listings(
        db: Session,
        user_id: int,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedPublicUserListings:
        PublicUserService._get_active_public_user(db, user_id)

        query = db.query(Listing).filter(
            Listing.owner_id == user_id,
            Listing.status == "published",
            Listing.moderation_status == "approved",
            Listing.deleted_at.is_(None),
        )

        total_items = query.count()
        total_pages = ceil(total_items / page_size) if total_items > 0 else 1
        offset = (page - 1) * page_size
        items = query.order_by(Listing.created_at.desc()).offset(offset).limit(page_size).all()

        return PaginatedPublicUserListings(
            page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=total_pages,
            items=items,
        )

    @staticmethod
    def search_public_users(
        db: Session,
        q: str,
        limit: int = 20,
    ) -> PublicUserSearchResponse:
        query_text = q.strip()
        if not query_text:
            return PublicUserSearchResponse(items=[])

        active_listing_counts = (
            db.query(
                Listing.owner_id.label("owner_id"),
                func.count(Listing.id).label("active_count"),
            )
            .filter(
                Listing.status == "published",
                Listing.moderation_status == "approved",
                Listing.deleted_at.is_(None),
            )
            .group_by(Listing.owner_id)
            .subquery()
        )

        search_pattern = f"%{query_text}%"
        rows = (
            db.query(User, func.coalesce(active_listing_counts.c.active_count, 0))
            .outerjoin(active_listing_counts, active_listing_counts.c.owner_id == User.id)
            .filter(
                User.account_status.notin_(["suspended", "deleted"]),
                or_(
                    User.full_name.ilike(search_pattern),
                    User.email.ilike(search_pattern),
                ),
            )
            .order_by(func.coalesce(active_listing_counts.c.active_count, 0).desc(), User.id.desc())
            .limit(limit)
            .all()
        )

        items = [
            PublicUserProfileRead(
                id=user.id,
                full_name=user.full_name,
                profile_image_url=user.profile_image_url,
                bio=user.bio,
                city=user.city,
                created_at=user.created_at,
                active_listings_count=int(active_count or 0),
            )
            for user, active_count in rows
        ]

        return PublicUserSearchResponse(items=items)
