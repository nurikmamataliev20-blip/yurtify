from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from datetime import datetime

class ListingImageBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    file_url: str
    is_primary: bool = False
    order_index: int = 0


class ListingImageRead(ListingImageBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    listing_id: int
    created_at: datetime

class ListingBase(BaseModel):
    title: str
    description: str
    price: float
    currency: str = "USD"
    city: str
    condition: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    is_negotiable: bool = False

class ListingCreate(ListingBase):
    category_id: int


class ListingSubmitForReview(BaseModel):
    submit: bool = True

class ListingUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    currency: Optional[str] = None
    city: Optional[str] = None
    category_id: Optional[int] = None
    condition: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    is_negotiable: Optional[bool] = None
    status: Optional[str] = None


class ListingListFilters(BaseModel):
    keyword: Optional[str] = None
    category_id: Optional[int] = None
    city: Optional[str] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    condition: Optional[str] = None
    promoted_only: bool = False
    sort_by: Optional[str] = Field(default=None)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)

class ListingRead(ListingBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_id: int
    category_id: int
    status: str
    moderation_status: str
    promotion_status: str
    is_promoted: bool = False
    promotion_type: Optional[str] = None
    view_count: int
    created_at: datetime
    updated_at: datetime
    images: List[ListingImageBase] = []


class PaginatedListings(BaseModel):
    page: int
    page_size: int
    total_items: int
    total_pages: int
    items: List[ListingRead]
