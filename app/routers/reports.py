from fastapi import Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_admin, get_current_user
from app.core.router import DualSlashAPIRouter
from app.models.models import User
from app.schemas.report_schemas import (
    PaginatedReports,
    ReportCreate,
    ReportRead,
    ReportReviewRequest,
)
from app.services.report_service import ReportService

router = DualSlashAPIRouter()


@router.post("/reports", response_model=ReportRead, status_code=status.HTTP_201_CREATED)
def create_report(
    payload: ReportCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return ReportService.create_report(db, current_user, payload)


@router.get("/reports/my", response_model=PaginatedReports)
def list_my_reports(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return ReportService.list_my_reports(db, current_user, page=page, page_size=page_size)


@router.get("/reports", response_model=PaginatedReports)
def list_reports(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    return ReportService.list_reports(db, page=page, page_size=page_size)


@router.patch("/reports/{report_id}", response_model=ReportRead)
def review_report(
    report_id: int,
    payload: ReportReviewRequest,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin),
):
    return ReportService.review_report(db, admin_user, report_id, payload)
