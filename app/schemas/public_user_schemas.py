from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class PublicUserProfileRead(BaseModel):
    id: int
    full_name: str
    profile_image_url: Optional[str] = None
    bio: Optional[str] = None
    city: str
    created_at: datetime
    active_listings_count: int


class PublicUserListingRead(BaseModel):
    id: int
    title: str
    price: float
    currency: str
    city: str
    condition: str
    created_at: datetime

    class Config:
        from_attributes = True


class PaginatedPublicUserListings(BaseModel):
    page: int
    page_size: int
    total_items: int
    total_pages: int
    items: List[PublicUserListingRead]
