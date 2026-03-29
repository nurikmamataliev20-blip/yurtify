from datetime import datetime, timezone
from math import ceil

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.models.models import Listing, Payment, Promotion, PromotionPackage, User
from app.schemas.promotion_schemas import PaginatedPromotions, PromotionCreateRequest
from app.services.payment_service import PaymentService


class PromotionService:
    @staticmethod
    def _expire_stale_promotions(db: Session, user_id: int | None = None) -> None:
        now = datetime.now(timezone.utc)
        query = db.query(Promotion).filter(Promotion.status == "active", Promotion.ends_at < now)
        if user_id is not None:
            query = query.filter(Promotion.user_id == user_id)

        stale_items = query.all()
        if not stale_items:
            return

        affected_listing_ids: set[int] = set()
        for promo in stale_items:
            promo.status = "expired"
            affected_listing_ids.add(promo.listing_id)

        db.flush()
        for listing_id in affected_listing_ids:
            PromotionService._sync_listing_promotion_status(db, listing_id)

        db.commit()

    @staticmethod
    def _sync_listing_promotion_status(db: Session, listing_id: int) -> None:
        now = datetime.now(timezone.utc)
        has_active = (
            db.query(Promotion)
            .filter(
                Promotion.listing_id == listing_id,
                Promotion.status == "active",
                Promotion.starts_at <= now,
                Promotion.ends_at > now,
            )
            .first()
            is not None
        )

        listing = db.query(Listing).filter(Listing.id == listing_id).first()
        if listing:
            listing.promotion_status = "active" if has_active else "none"

    @staticmethod
    def _decorate_promotion(promotion: Promotion) -> Promotion:
        package_name = promotion.promotion_package.name if promotion.promotion_package else None
        setattr(promotion, "package_name", package_name)
        return promotion

    @staticmethod
    def create_promotion(db: Session, current_user: User, payload: PromotionCreateRequest) -> Promotion:
        listing = (
            db.query(Listing)
            .filter(Listing.id == payload.listing_id, Listing.deleted_at.is_(None))
            .first()
        )
        if not listing:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found")

        if listing.owner_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only listing owner can activate promotion",
            )

        package = (
            db.query(PromotionPackage)
            .filter(PromotionPackage.id == payload.package_id, PromotionPackage.is_active.is_(True))
            .first()
        )
        if not package:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Promotion package not found")

        payment = db.query(Payment).filter(Payment.id == payload.payment_id).first()
        if not payment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")

        if payment.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

        if payment.listing_id != payload.listing_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Payment does not belong to the selected listing",
            )

        if payment.promotion_package_id != payload.package_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Payment package mismatch",
            )

        if payment.status == "pending":
            payment = PaymentService.confirm_payment(db, current_user, payload.payment_id)
        elif payment.status != "successful":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Payment must be successful before activation",
            )

        promotion = payment.promotion
        if not promotion:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Related promotion not found")

        if payload.target_city is not None:
            promotion.target_city = payload.target_city
        if payload.target_category_id is not None:
            promotion.target_category_id = payload.target_category_id

        db.commit()
        db.refresh(promotion)
        return PromotionService._decorate_promotion(promotion)

    @staticmethod
    def list_my_promotions(
        db: Session,
        current_user: User,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedPromotions:
        PromotionService._expire_stale_promotions(db, user_id=current_user.id)

        query = (
            db.query(Promotion)
            .options(joinedload(Promotion.promotion_package))
            .filter(Promotion.user_id == current_user.id)
        )

        total_items = query.count()
        total_pages = ceil(total_items / page_size) if total_items > 0 else 1
        offset = (page - 1) * page_size

        items = query.order_by(Promotion.created_at.desc()).offset(offset).limit(page_size).all()
        items = [PromotionService._decorate_promotion(item) for item in items]

        return PaginatedPromotions(
            page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=total_pages,
            items=items,
        )

    @staticmethod
    def get_promotion(db: Session, current_user: User, promotion_id: int) -> Promotion:
        PromotionService._expire_stale_promotions(db, user_id=current_user.id)

        promotion = (
            db.query(Promotion)
            .options(joinedload(Promotion.promotion_package))
            .filter(Promotion.id == promotion_id)
            .first()
        )
        if not promotion:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Promotion not found")

        if promotion.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

        return PromotionService._decorate_promotion(promotion)

    @staticmethod
    def cancel_promotion(db: Session, current_user: User, promotion_id: int) -> None:
        promotion = db.query(Promotion).filter(Promotion.id == promotion_id).first()
        if not promotion:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Promotion not found")

        if promotion.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

        if promotion.status != "active":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only active promotions can be cancelled",
            )

        promotion.status = "cancelled"
        PromotionService._sync_listing_promotion_status(db, promotion.listing_id)
        db.commit()
