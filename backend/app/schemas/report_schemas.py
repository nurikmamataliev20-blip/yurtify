from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


ReportTargetType = Literal["listing", "user"]
ReportStatusType = Literal["pending", "reviewed", "resolved"]


class ReportCreate(BaseModel):
    target_type: ReportTargetType
    target_id: int = Field(..., ge=1)
    reason_code: str = Field(..., min_length=2, max_length=50)
    reason_text: Optional[str] = Field(default=None, max_length=1000)


class ReportReviewRequest(BaseModel):
    status: ReportStatusType
    resolution_note: Optional[str] = Field(default=None, max_length=2000)


class ReportRead(BaseModel):
    id: int
    reporter_user_id: int
    target_type: str
    target_id: int
    reason_code: str
    reason_text: Optional[str] = None
    status: str
    resolution_note: Optional[str] = None
    reviewed_by_admin_id: Optional[int] = None
    created_at: datetime
    reviewed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PaginatedReports(BaseModel):
    page: int
    page_size: int
    total_items: int
    total_pages: int
    items: List[ReportRead]
