from datetime import datetime, timezone
from math import ceil

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.models import Listing, Report, User
from app.schemas.report_schemas import PaginatedReports, ReportCreate, ReportReviewRequest


class ReportService:
    @staticmethod
    def create_report(db: Session, current_user: User, payload: ReportCreate) -> Report:
        if payload.target_type == "listing":
            listing = db.query(Listing).filter(Listing.id == payload.target_id, Listing.deleted_at.is_(None)).first()
            if not listing:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found")
        elif payload.target_type == "user":
            target_user = db.query(User).filter(User.id == payload.target_id).first()
            if not target_user:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
            if target_user.id == current_user.id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot report yourself")
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid target_type")

        duplicate = (
            db.query(Report)
            .filter(
                Report.reporter_user_id == current_user.id,
                Report.target_type == payload.target_type,
                Report.target_id == payload.target_id,
                Report.reason_code == payload.reason_code,
                Report.status.in_(["pending", "reviewed"]),
            )
            .first()
        )
        if duplicate:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Duplicate report detected")

        report = Report(
            reporter_user_id=current_user.id,
            target_type=payload.target_type,
            target_id=payload.target_id,
            reason_code=payload.reason_code,
            reason_text=payload.reason_text,
            status="pending",
        )
        db.add(report)
        db.commit()
        db.refresh(report)
        return report

    @staticmethod
    def list_reports(db: Session, page: int = 1, page_size: int = 20) -> PaginatedReports:
        query = db.query(Report)

        total_items = query.count()
        total_pages = ceil(total_items / page_size) if total_items > 0 else 1
        offset = (page - 1) * page_size
        items = query.order_by(Report.created_at.desc()).offset(offset).limit(page_size).all()

        return PaginatedReports(
            page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=total_pages,
            items=items,
        )

    @staticmethod
    def list_my_reports(
        db: Session,
        current_user: User,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedReports:
        query = db.query(Report).filter(Report.reporter_user_id == current_user.id)

        total_items = query.count()
        total_pages = ceil(total_items / page_size) if total_items > 0 else 1
        offset = (page - 1) * page_size
        items = query.order_by(Report.created_at.desc()).offset(offset).limit(page_size).all()

        return PaginatedReports(
            page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=total_pages,
            items=items,
        )

    @staticmethod
    def review_report(db: Session, admin_user: User, report_id: int, payload: ReportReviewRequest) -> Report:
        report = db.query(Report).filter(Report.id == report_id).first()
        if not report:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

        report.status = payload.status
        report.resolution_note = payload.resolution_note
        report.reviewed_by_admin_id = admin_user.id
        report.reviewed_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(report)
        return report
