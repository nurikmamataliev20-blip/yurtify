from datetime import datetime
from typing import List

from pydantic import BaseModel


class FavoriteListingSummary(BaseModel):
    id: int
    title: str
    price: float
    currency: str
    city: str
    status: str
    moderation_status: str

    class Config:
        from_attributes = True


class FavoriteRead(BaseModel):
    id: int
    listing_id: int
    created_at: datetime
    listing: FavoriteListingSummary

    class Config:
        from_attributes = True


class PaginatedFavorites(BaseModel):
    page: int
    page_size: int
    total_items: int
    total_pages: int
    items: List[FavoriteRead]
