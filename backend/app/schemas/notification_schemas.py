from datetime import datetime
from typing import List, Literal

from pydantic import BaseModel


NotificationType = Literal[
    "new_message",
    "listing_approved",
    "listing_rejected",
    "payment_success",
    "promotion_activated",
]


class NotificationRead(BaseModel):
    id: int
    user_id: int
    type: str
    title: str
    body: str
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True


class PaginatedNotifications(BaseModel):
    page: int
    page_size: int
    total_items: int
    total_pages: int
    items: List[NotificationRead]
