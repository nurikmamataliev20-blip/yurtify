from datetime import datetime, timezone
from math import ceil

from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.models.models import Conversation, Listing, Message, User
from app.schemas.messaging_schemas import (
    ConversationStartRequest,
    MessageCreate,
    PaginatedConversations,
    PaginatedMessages,
)
from app.services.notification_service import NotificationService


class MessagingService:
    @staticmethod
    def _normalize_participants(user_a_id: int, user_b_id: int) -> tuple[int, int]:
        return (user_a_id, user_b_id) if user_a_id < user_b_id else (user_b_id, user_a_id)

    @staticmethod
    def _get_user_conversation(db: Session, conversation_id: int, current_user_id: int) -> Conversation:
        conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if not conversation:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

        if current_user_id not in {conversation.participant_a_id, conversation.participant_b_id}:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

        return conversation

    @staticmethod
    def start_conversation(db: Session, current_user: User, payload: ConversationStartRequest) -> Conversation:
        if current_user.id == payload.recipient_user_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Users cannot message themselves")

        listing = db.query(Listing).filter(Listing.id == payload.listing_id, Listing.deleted_at.is_(None)).first()
        if not listing:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found")

        recipient = db.query(User).filter(User.id == payload.recipient_user_id).first()
        if not recipient:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipient user not found")

        if listing.owner_id not in {current_user.id, payload.recipient_user_id}:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Conversation participants must include listing owner",
            )

        participant_a_id, participant_b_id = MessagingService._normalize_participants(
            current_user.id, payload.recipient_user_id
        )

        existing = (
            db.query(Conversation)
            .filter(
                Conversation.listing_id == payload.listing_id,
                Conversation.participant_a_id == participant_a_id,
                Conversation.participant_b_id == participant_b_id,
            )
            .first()
        )
        if existing:
            return existing

        conversation = Conversation(
            listing_id=payload.listing_id,
            participant_a_id=participant_a_id,
            participant_b_id=participant_b_id,
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
        return conversation

    @staticmethod
    def list_conversations(
        db: Session,
        current_user: User,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedConversations:
        query = db.query(Conversation).filter(
            or_(
                Conversation.participant_a_id == current_user.id,
                Conversation.participant_b_id == current_user.id,
            )
        )

        total_items = query.count()
        total_pages = ceil(total_items / page_size) if total_items > 0 else 1
        offset = (page - 1) * page_size

        items = (
            query.order_by(
                Conversation.last_message_at.is_(None),
                Conversation.last_message_at.desc(),
                Conversation.created_at.desc(),
            )
            .offset(offset)
            .limit(page_size)
            .all()
        )

        return PaginatedConversations(
            page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=total_pages,
            items=items,
        )

    @staticmethod
    def get_conversation(db: Session, current_user: User, conversation_id: int) -> Conversation:
        return MessagingService._get_user_conversation(db, conversation_id, current_user.id)

    @staticmethod
    def create_message(db: Session, current_user: User, payload: MessageCreate) -> Message:
        conversation = MessagingService._get_user_conversation(db, payload.conversation_id, current_user.id)

        text_body = (payload.text_body or "").strip()
        if payload.message_type == "text" and not text_body:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Text message cannot be empty")

        message = Message(
            conversation_id=conversation.id,
            sender_id=current_user.id,
            message_type=payload.message_type,
            text_body=text_body,
            is_read=False,
        )
        db.add(message)

        now = datetime.now(timezone.utc)
        conversation.last_message_at = now
        db.flush()

        recipient_id = (
            conversation.participant_b_id
            if current_user.id == conversation.participant_a_id
            else conversation.participant_a_id
        )
        NotificationService.create_notification(
            db=db,
            user_id=recipient_id,
            notification_type="new_message",
            title="New message",
            body=f"You received a new message for listing #{conversation.listing_id}",
        )

        db.commit()
        return (
            db.query(Message)
            .options(joinedload(Message.attachments))
            .filter(Message.id == message.id)
            .first()
        )

    @staticmethod
    def list_messages(
        db: Session,
        current_user: User,
        conversation_id: int,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedMessages:
        conversation = MessagingService._get_user_conversation(db, conversation_id, current_user.id)

        query = (
            db.query(Message)
            .options(joinedload(Message.attachments))
            .filter(
                Message.conversation_id == conversation.id,
                Message.deleted_at.is_(None),
            )
        )

        total_items = query.count()
        total_pages = ceil(total_items / page_size) if total_items > 0 else 1
        offset = (page - 1) * page_size

        items = query.order_by(Message.sent_at.asc()).offset(offset).limit(page_size).all()

        unread_ids = [m.id for m in items if m.sender_id != current_user.id and not m.is_read]
        if unread_ids:
            (
                db.query(Message)
                .filter(Message.id.in_(unread_ids))
                .update({Message.is_read: True}, synchronize_session=False)
            )
            db.commit()
            items = query.order_by(Message.sent_at.asc()).offset(offset).limit(page_size).all()

        return PaginatedMessages(
            page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=total_pages,
            items=items,
        )
