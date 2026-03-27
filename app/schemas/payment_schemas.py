from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


PaymentStatus = Literal["pending", "successful", "failed", "cancelled", "refunded"]


class PaymentInitiateRequest(BaseModel):
    listing_id: int = Field(..., ge=1)
    promotion_package_id: int = Field(..., ge=1)
    target_city: Optional[str] = Field(default=None, max_length=100)
    target_category_id: Optional[int] = Field(default=None, ge=1)


class PaymentRead(BaseModel):
    id: int
    user_id: int
    listing_id: Optional[int] = None
    promotion_package_id: Optional[int] = None
    amount: float
    currency: str
    status: str
    payment_provider: str
    provider_reference: Optional[str] = None
    created_at: datetime
    paid_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PaymentInitiateResponse(BaseModel):
    payment_id: int
    mock_payment_url: str
    payment: PaymentRead


class PaginatedPayments(BaseModel):
    page: int
    page_size: int
    total_items: int
    total_pages: int
    items: List[PaymentRead]
