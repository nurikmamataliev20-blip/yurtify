from datetime import datetime, timezone
from math import ceil

from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.dependencies import is_admin_user
from app.models.models import Category, Listing, User
from app.schemas.listing_schemas import ListingCreate, ListingListFilters, ListingUpdate, PaginatedListings


class ListingService:
    @staticmethod
    def create_listing(db: Session, current_user: User, listing_in: ListingCreate) -> Listing:
        if current_user.account_status in {"suspended", "deleted", "blocked"}:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Blocked users cannot create listings",
            )

        category = db.query(Category).filter(Category.id == listing_in.category_id, Category.is_active.is_(True)).first()
        if not category:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Category is invalid or inactive")

        listing = Listing(
            **listing_in.model_dump(),
            owner_id=current_user.id,
            status="draft",
            moderation_status="pending",
        )
        db.add(listing)
        db.commit()
        db.refresh(listing)
        return listing

    @staticmethod
    def get_public_feed(db: Session, filters: ListingListFilters) -> PaginatedListings:
        query = db.query(Listing).filter(
            Listing.deleted_at.is_(None),
            Listing.status == "published",
            Listing.moderation_status == "approved",
        )

        if filters.keyword:
            like_q = f"%{filters.keyword}%"
            query = query.filter(
                or_(
                    Listing.title.ilike(like_q),
                    Listing.description.ilike(like_q),
                )
            )

        if filters.category_id is not None:
            query = query.filter(Listing.category_id == filters.category_id)
        if filters.city:
            query = query.filter(Listing.city == filters.city)
        if filters.min_price is not None:
            query = query.filter(Listing.price >= filters.min_price)
        if filters.max_price is not None:
            query = query.filter(Listing.price <= filters.max_price)
        if filters.condition:
            query = query.filter(Listing.condition == filters.condition)

        sort_mapping = {
            "newest": Listing.created_at.desc(),
            "oldest": Listing.created_at.asc(),
            "price_asc": Listing.price.asc(),
            "price_desc": Listing.price.desc(),
        }
        query = query.order_by(sort_mapping.get(filters.sort_by, Listing.created_at.desc()))

        total_items = query.count()
        total_pages = ceil(total_items / filters.page_size) if total_items > 0 else 1
        offset = (filters.page - 1) * filters.page_size

        items = query.offset(offset).limit(filters.page_size).all()

        return PaginatedListings(
            page=filters.page,
            page_size=filters.page_size,
            total_items=total_items,
            total_pages=total_pages,
            items=items,
        )

    @staticmethod
    def get_listing_detail(db: Session, listing_id: int) -> Listing:
        listing = db.query(Listing).filter(Listing.id == listing_id, Listing.deleted_at.is_(None)).first()
        if not listing:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found")

        if not (listing.status == "published" and listing.moderation_status == "approved"):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found")

        listing.view_count += 1
        db.commit()
        db.refresh(listing)
        return listing

    @staticmethod
    def get_my_listings(
        db: Session,
        current_user: User,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedListings:
        query = db.query(Listing).filter(
            Listing.owner_id == current_user.id,
            Listing.deleted_at.is_(None),
        )

        total_items = query.count()
        total_pages = ceil(total_items / page_size) if total_items > 0 else 1
        offset = (page - 1) * page_size
        items = query.order_by(Listing.created_at.desc()).offset(offset).limit(page_size).all()

        return PaginatedListings(
            page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=total_pages,
            items=items,
        )

    @staticmethod
    def update_listing(db: Session, current_user: User, listing_id: int, listing_in: ListingUpdate) -> Listing:
        listing = db.query(Listing).filter(Listing.id == listing_id, Listing.deleted_at.is_(None)).first()
        if not listing:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found")

        if listing.owner_id != current_user.id and not is_admin_user(current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only owner or admin can edit listing",
            )

        update_data = listing_in.model_dump(exclude_unset=True)

        if "category_id" in update_data:
            category = db.query(Category).filter(Category.id == update_data["category_id"], Category.is_active.is_(True)).first()
            if not category:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Category is invalid or inactive")

        for key, value in update_data.items():
            setattr(listing, key, value)

        if listing.status == "pending_review":
            listing.moderation_status = "pending"
        elif listing.status == "published":
            listing.moderation_status = "approved"
            if not listing.published_at:
                listing.published_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(listing)
        return listing

    @staticmethod
    def soft_delete_listing(db: Session, current_user: User, listing_id: int) -> None:
        listing = db.query(Listing).filter(Listing.id == listing_id, Listing.deleted_at.is_(None)).first()
        if not listing:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found")

        if listing.owner_id != current_user.id and not is_admin_user(current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only owner or admin can delete listing",
            )

        listing.deleted_at = datetime.now(timezone.utc)
        listing.status = "archived"
        db.commit()
