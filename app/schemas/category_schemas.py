from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


class CategoryBase(BaseModel):
    name: str
    slug: str
    parent_category_id: Optional[int] = None
    display_order: int = 0


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    parent_category_id: Optional[int] = None
    display_order: Optional[int] = None
    is_active: Optional[bool] = None


class CategoryRead(BaseModel):
    id: int
    name: str
    slug: str
    parent_category_id: Optional[int] = None
    is_active: bool
    display_order: int
    created_at: datetime

    class Config:
        from_attributes = True


class CategoryListResponse(BaseModel):
    items: List[CategoryRead]
