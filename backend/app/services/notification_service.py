from math import ceil

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.models import Notification, User
from app.schemas.notification_schemas import PaginatedNotifications


class NotificationService:
    @staticmethod
    def create_notification(
        db: Session,
        user_id: int,
        notification_type: str,
        title: str,
        body: str,
    ) -> Notification:
        notification = Notification(
            user_id=user_id,
            type=notification_type,
            title=title,
            body=body,
            is_read=False,
        )
        db.add(notification)
        db.flush()
        return notification

    @staticmethod
    def list_notifications(
        db: Session,
        current_user: User,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedNotifications:
        query = db.query(Notification).filter(Notification.user_id == current_user.id)
        total_items = query.count()
        total_pages = ceil(total_items / page_size) if total_items > 0 else 1
        offset = (page - 1) * page_size

        items = query.order_by(Notification.created_at.desc()).offset(offset).limit(page_size).all()

        return PaginatedNotifications(
            page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=total_pages,
            items=items,
        )

    @staticmethod
    def mark_as_read(db: Session, current_user: User, notification_id: int) -> Notification:
        notification = (
            db.query(Notification)
            .filter(Notification.id == notification_id, Notification.user_id == current_user.id)
            .first()
        )
        if not notification:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")

        if not notification.is_read:
            notification.is_read = True
            db.commit()
            db.refresh(notification)

        return notification

    @staticmethod
    def get_unread_count(db: Session, current_user: User) -> int:
        return (
            db.query(Notification)
            .filter(Notification.user_id == current_user.id, Notification.is_read.is_(False))
            .count()
        )

    @staticmethod
    def mark_all_as_read(db: Session, current_user: User) -> int:
        unread_notifications = (
            db.query(Notification)
            .filter(Notification.user_id == current_user.id, Notification.is_read.is_(False))
            .all()
        )

        if not unread_notifications:
            return 0

        for notification in unread_notifications:
            notification.is_read = True

        db.commit()
        return len(unread_notifications)
