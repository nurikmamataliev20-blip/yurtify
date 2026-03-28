from fastapi import Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.router import DualSlashAPIRouter
from app.models.models import User
from app.schemas.notification_schemas import NotificationRead, PaginatedNotifications
from app.services.notification_service import NotificationService

router = DualSlashAPIRouter()


@router.get("/notifications", response_model=PaginatedNotifications)
def list_notifications(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return NotificationService.list_notifications(db, current_user, page=page, page_size=page_size)


@router.get("/notifications/unread-count")
def get_unread_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    unread_count = NotificationService.get_unread_count(db, current_user)
    return {"unread_count": unread_count}


@router.patch("/notifications/{notification_id}/read", response_model=NotificationRead)
def mark_notification_as_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return NotificationService.mark_as_read(db, current_user, notification_id)


@router.patch("/notifications/read-all")
def mark_all_notifications_as_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    marked_count = NotificationService.mark_all_as_read(db, current_user)
    return {"marked_count": marked_count}
