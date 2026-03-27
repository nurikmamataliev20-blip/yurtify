from datetime import datetime, timedelta, timezone
from math import ceil

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.models import Listing, Payment, Promotion, PromotionPackage, User
from app.schemas.payment_schemas import PaymentInitiateRequest, PaymentInitiateResponse, PaginatedPayments
from app.services.notification_service import NotificationService


class PaymentService:
    PENDING_TIMEOUT_MINUTES = 30

    @staticmethod
    def _expire_stale_pending_payments(db: Session, user_id: int | None = None) -> None:
        now = datetime.now(timezone.utc)
        query = db.query(Payment).filter(
            Payment.status == "pending",
            Payment.expires_at.is_not(None),
            Payment.expires_at < now,
        )
        if user_id is not None:
            query = query.filter(Payment.user_id == user_id)

        stale_payments = query.all()
        if not stale_payments:
            return

        listing_ids: set[int] = set()
        for pay in stale_payments:
            pay.status = "failed"
            if pay.promotion is not None and pay.promotion.status == "pending":
                pay.promotion.status = "cancelled"
                listing_ids.add(pay.promotion.listing_id)

        for listing_id in listing_ids:
            PaymentService._sync_listing_promotion_status(db, listing_id)

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
    def _get_payment_for_owner(db: Session, current_user: User, payment_id: int) -> Payment:
        payment = db.query(Payment).filter(Payment.id == payment_id).first()
        if not payment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
        if payment.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        return payment

    @staticmethod
    def initiate_payment(
        db: Session,
        current_user: User,
        payload: PaymentInitiateRequest,
    ) -> PaymentInitiateResponse:
        PaymentService._expire_stale_pending_payments(db, user_id=current_user.id)

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
                detail="Only listing owner can initiate payment",
            )

        if not (listing.status == "published" and listing.moderation_status == "approved"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Listing must be published and approved to be promoted",
            )

        package = (
            db.query(PromotionPackage)
            .filter(PromotionPackage.id == payload.promotion_package_id, PromotionPackage.is_active.is_(True))
            .first()
        )
        if not package:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Promotion package not found")

        now = datetime.now(timezone.utc)
        active_promotion = (
            db.query(Promotion)
            .filter(
                Promotion.listing_id == listing.id,
                Promotion.status == "active",
                Promotion.starts_at <= now,
                Promotion.ends_at > now,
            )
            .first()
        )
        if active_promotion:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Listing already has an active promotion",
            )

        promotion = Promotion(
            listing_id=listing.id,
            user_id=current_user.id,
            promotion_package_id=package.id,
            promotion_type=package.promotion_type,
            target_city=payload.target_city,
            target_category_id=payload.target_category_id,
            starts_at=now,
            ends_at=now,
            status="pending",
            purchased_price=package.price,
        )
        db.add(promotion)
        db.flush()

        payment = Payment(
            user_id=current_user.id,
            listing_id=listing.id,
            promotion_id=promotion.id,
            promotion_package_id=package.id,
            amount=package.price,
            currency=package.currency,
            status="pending",
            payment_provider="mock",
            provider_reference=f"mock-init-{promotion.id}",
            expires_at=now + timedelta(minutes=PaymentService.PENDING_TIMEOUT_MINUTES),
        )
        db.add(payment)
        db.commit()
        db.refresh(payment)

        return PaymentInitiateResponse(
            payment_id=payment.id,
            mock_payment_url=f"https://mock-pay.example.com/pay/{payment.id}",
            payment=payment,
        )

    @staticmethod
    def list_my_payments(
        db: Session,
        current_user: User,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedPayments:
        PaymentService._expire_stale_pending_payments(db, user_id=current_user.id)

        query = db.query(Payment).filter(Payment.user_id == current_user.id)

        total_items = query.count()
        total_pages = ceil(total_items / page_size) if total_items > 0 else 1
        offset = (page - 1) * page_size

        items = query.order_by(Payment.created_at.desc()).offset(offset).limit(page_size).all()

        return PaginatedPayments(
            page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=total_pages,
            items=items,
        )

    @staticmethod
    def get_payment(db: Session, current_user: User, payment_id: int) -> Payment:
        PaymentService._expire_stale_pending_payments(db, user_id=current_user.id)
        return PaymentService._get_payment_for_owner(db, current_user, payment_id)

    @staticmethod
    def confirm_payment(db: Session, current_user: User, payment_id: int) -> Payment:
        PaymentService._expire_stale_pending_payments(db, user_id=current_user.id)
        payment = PaymentService._get_payment_for_owner(db, current_user, payment_id)

        if payment.status != "pending":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only pending payment can be confirmed",
            )

        now = datetime.now(timezone.utc)
        if payment.expires_at and payment.expires_at < now:
            payment.status = "failed"
            if payment.promotion is not None:
                payment.promotion.status = "cancelled"
                PaymentService._sync_listing_promotion_status(db, payment.promotion.listing_id)
            db.commit()
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Payment has expired")

        if not payment.promotion:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Related promotion not found")
        if not payment.promotion_package:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Promotion package not found")

        payment.status = "successful"
        payment.paid_at = now
        payment.provider_reference = f"mock-success-{payment.id}"

        promotion = payment.promotion
        promotion.status = "active"
        promotion.starts_at = now
        promotion.ends_at = now + timedelta(days=payment.promotion_package.duration_days)

        PaymentService._sync_listing_promotion_status(db, promotion.listing_id)

        NotificationService.create_notification(
            db=db,
            user_id=current_user.id,
            notification_type="payment_successful",
            title="Payment successful",
            body=f"Payment #{payment.id} was completed successfully.",
        )
        NotificationService.create_notification(
            db=db,
            user_id=current_user.id,
            notification_type="promotion_activated",
            title="Promotion activated",
            body=f"Your listing #{promotion.listing_id} is now promoted.",
        )

        db.commit()
        db.refresh(payment)
        return payment

    @staticmethod
    def cancel_payment(db: Session, current_user: User, payment_id: int) -> Payment:
        PaymentService._expire_stale_pending_payments(db, user_id=current_user.id)
        payment = PaymentService._get_payment_for_owner(db, current_user, payment_id)

        if payment.status != "pending":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only pending payment can be cancelled",
            )

        payment.status = "cancelled"
        payment.provider_reference = f"mock-cancel-{payment.id}"

        if payment.promotion:
            payment.promotion.status = "cancelled"
            PaymentService._sync_listing_promotion_status(db, payment.promotion.listing_id)

        db.commit()
        db.refresh(payment)
        return payment
