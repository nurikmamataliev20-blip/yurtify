from datetime import datetime, timezone
from math import ceil

from fastapi import HTTPException, status
from sqlalchemy import case, or_
from sqlalchemy.orm import Session

from app.core.dependencies import is_admin_user
from app.models.models import Category, Listing, Promotion, User
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
            status="published",
            moderation_status="approved",
            published_at=datetime.now(timezone.utc),
        )
        db.add(listing)
        db.commit()
        db.refresh(listing)
        return listing

    @staticmethod
    def get_public_feed(db: Session, filters: ListingListFilters) -> PaginatedListings:
        now = datetime.now(timezone.utc)
        active_promotion_subquery = (
            db.query(
                Promotion.listing_id.label("listing_id"),
                Promotion.promotion_type.label("promotion_type"),
            )
            .filter(
                Promotion.status == "active",
                Promotion.starts_at <= now,
                Promotion.ends_at > now,
            )
            .subquery()
        )

        query = db.query(Listing).filter(
            Listing.deleted_at.is_(None),
            Listing.status == "published",
            Listing.moderation_status == "approved",
        )
        query = query.outerjoin(
            active_promotion_subquery,
            active_promotion_subquery.c.listing_id == Listing.id,
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

        if filters.promoted_only:
            query = query.filter(active_promotion_subquery.c.listing_id.isnot(None))

        sort_mapping = {
            "newest": Listing.created_at.desc(),
            "oldest": Listing.created_at.asc(),
            "price_asc": Listing.price.asc(),
            "price_desc": Listing.price.desc(),
        }

        if filters.sort_by:
            query = query.order_by(sort_mapping.get(filters.sort_by, Listing.created_at.desc()))
        else:
            query = query.order_by(
                case((active_promotion_subquery.c.listing_id.isnot(None), 0), else_=1),
                Listing.created_at.desc(),
            )

        total_items = query.count()
        total_pages = ceil(total_items / filters.page_size) if total_items > 0 else 1
        offset = (filters.page - 1) * filters.page_size

        rows = (
            query.with_entities(Listing, active_promotion_subquery.c.promotion_type)
            .offset(offset)
            .limit(filters.page_size)
            .all()
        )
        items = []
        for listing, promotion_type in rows:
            setattr(listing, "is_promoted", promotion_type is not None)
            setattr(listing, "promotion_type", promotion_type)
            items.append(listing)

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

        now = datetime.now(timezone.utc)
        active_promotion = (
            db.query(Promotion)
            .filter(
                Promotion.listing_id == listing.id,
                Promotion.status == "active",
                Promotion.starts_at <= now,
                Promotion.ends_at > now,
            )
            .order_by(Promotion.created_at.desc())
            .first()
        )
        setattr(listing, "is_promoted", active_promotion is not None)
        setattr(listing, "promotion_type", active_promotion.promotion_type if active_promotion else None)
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

        now = datetime.now(timezone.utc)
        listing_ids = [item.id for item in items]
        promotion_map = {}
        if listing_ids:
            active_promotions = (
                db.query(Promotion)
                .filter(
                    Promotion.listing_id.in_(listing_ids),
                    Promotion.status == "active",
                    Promotion.starts_at <= now,
                    Promotion.ends_at > now,
                )
                .all()
            )
            for promotion in active_promotions:
                if promotion.listing_id not in promotion_map:
                    promotion_map[promotion.listing_id] = promotion.promotion_type

        for item in items:
            promo_type = promotion_map.get(item.id)
            setattr(item, "is_promoted", promo_type is not None)
            setattr(item, "promotion_type", promo_type)

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
