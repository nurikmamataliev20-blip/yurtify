from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.models import User
from app.schemas.messaging_schemas import (
    ConversationRead,
    ConversationStartRequest,
    MessageCreate,
    MessageRead,
    PaginatedConversations,
    PaginatedMessages,
)
from app.services.messaging_service import MessagingService

router = APIRouter()


@router.post("/conversations", response_model=ConversationRead, status_code=status.HTTP_201_CREATED)
def start_conversation(
    payload: ConversationStartRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return MessagingService.start_conversation(db, current_user, payload)


@router.get("/conversations", response_model=PaginatedConversations)
def list_conversations(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return MessagingService.list_conversations(db, current_user, page=page, page_size=page_size)


@router.get("/conversations/{conversation_id}", response_model=ConversationRead)
def get_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return MessagingService.get_conversation(db, current_user, conversation_id)


@router.post("/messages", response_model=MessageRead, status_code=status.HTTP_201_CREATED)
def create_message(
    payload: MessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return MessagingService.create_message(db, current_user, payload)


@router.get("/messages/{conversation_id}", response_model=PaginatedMessages)
def list_messages(
    conversation_id: int,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return MessagingService.list_messages(
        db,
        current_user,
        conversation_id=conversation_id,
        page=page,
        page_size=page_size,
    )
