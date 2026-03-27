from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel


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


class PaginatedPromotions(BaseModel):
    page: int
    page_size: int
    total_items: int
    total_pages: int
    items: List[PromotionRead]
