from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


PromotionType = Literal[
    "featured",
    "boosted",
    "top_placement",
    "city_targeted",
    "category_targeted",
]


class PromotionPackageRead(BaseModel):
    id: int
    name: str
    price: float
    currency: str
    duration_days: int
    promotion_type: str
    description: Optional[str] = None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class PaginatedPromotionPackages(BaseModel):
    page: int
    page_size: int
    total_items: int
    total_pages: int
    items: List[PromotionPackageRead]


class PromotionPackageSeedItem(BaseModel):
    name: str
    price: float = Field(..., ge=0)
    currency: str = Field(default="KGS", max_length=10)
    duration_days: int = Field(..., ge=1)
    promotion_type: PromotionType
    description: Optional[str] = None
