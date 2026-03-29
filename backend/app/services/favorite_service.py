from math import ceil

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.models.models import Favorite, Listing, User
from app.schemas.favorite_schemas import PaginatedFavorites


class FavoriteService:
    @staticmethod
    def _get_listing_for_favorite(db: Session, listing_id: int) -> Listing:
        listing = db.query(Listing).filter(Listing.id == listing_id).first()
        if not listing or listing.deleted_at is not None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found")

        if listing.status == "archived":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Archived listings cannot be added to favorites",
            )

        return listing

    @staticmethod
    def add_to_favorites(db: Session, current_user: User, listing_id: int) -> Favorite:
        FavoriteService._get_listing_for_favorite(db, listing_id)

        existing = (
            db.query(Favorite)
            .filter(Favorite.user_id == current_user.id, Favorite.listing_id == listing_id)
            .first()
        )
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Listing already in favorites")

        favorite = Favorite(user_id=current_user.id, listing_id=listing_id)
        db.add(favorite)
        db.commit()

        return (
            db.query(Favorite)
            .options(joinedload(Favorite.listing))
            .filter(Favorite.id == favorite.id)
            .first()
        )

    @staticmethod
    def remove_from_favorites(db: Session, current_user: User, listing_id: int) -> None:
        favorite = (
            db.query(Favorite)
            .filter(Favorite.user_id == current_user.id, Favorite.listing_id == listing_id)
            .first()
        )
        if not favorite:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Favorite not found")

        db.delete(favorite)
        db.commit()

    @staticmethod
    def list_user_favorites(
        db: Session,
        current_user: User,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedFavorites:
        query = (
            db.query(Favorite)
            .options(joinedload(Favorite.listing))
            .join(Listing, Favorite.listing_id == Listing.id)
            .filter(
                Favorite.user_id == current_user.id,
                Listing.deleted_at.is_(None),
                Listing.status != "archived",
            )
        )

        total_items = query.count()
        total_pages = ceil(total_items / page_size) if total_items > 0 else 1
        offset = (page - 1) * page_size

        items = query.order_by(Favorite.created_at.desc()).offset(offset).limit(page_size).all()

        return PaginatedFavorites(
            page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=total_pages,
            items=items,
        )
