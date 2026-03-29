from fastapi import Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.router import DualSlashAPIRouter
from app.models.models import User
from app.schemas.payment_schemas import PaymentInitiateRequest, PaymentInitiateResponse, PaymentRead, PaginatedPayments
from app.services.payment_service import PaymentService

router = DualSlashAPIRouter()


@router.post("/payments/initiate", response_model=PaymentInitiateResponse, status_code=status.HTTP_201_CREATED)
def initiate_payment(
    payload: PaymentInitiateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return PaymentService.initiate_payment(db, current_user, payload)


@router.get("/payments/my", response_model=PaginatedPayments)
def list_my_payments(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return PaymentService.list_my_payments(db, current_user, page=page, page_size=page_size)


@router.get("/payments/{payment_id}", response_model=PaymentRead)
def get_payment(
    payment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return PaymentService.get_payment(db, current_user, payment_id)


@router.post("/payments/{payment_id}/confirm", response_model=PaymentRead)
def confirm_payment(
    payment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return PaymentService.confirm_payment(db, current_user, payment_id)


@router.post("/payments/{payment_id}/cancel", response_model=PaymentRead)
def cancel_payment(
    payment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return PaymentService.cancel_payment(db, current_user, payment_id)
