from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


PromotionStatus = Literal["pending", "active", "expired", "cancelled"]


class PromotionRead(BaseModel):
    id: int
    listing_id: int
    user_id: int
    promotion_type: str
    target_city: Optional[str] = None
    target_category_id: Optional[int] = None
    starts_at: datetime
    ends_at: datetime
    status: str
    purchased_price: float
    package_name: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class PromotionCreateRequest(BaseModel):
    listing_id: int = Field(..., ge=1)
    package_id: int = Field(..., ge=1)
    payment_id: int = Field(..., ge=1)
    target_city: Optional[str] = Field(default=None, max_length=100)
    target_category_id: Optional[int] = Field(default=None, ge=1)


class PaginatedPromotions(BaseModel):
    page: int
    page_size: int
    total_items: int
    total_pages: int
    items: List[PromotionRead]
