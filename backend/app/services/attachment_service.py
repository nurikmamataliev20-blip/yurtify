from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.config import UPLOADS_DIR
from app.models.models import Conversation, Message, MessageAttachment, User


class AttachmentService:
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    ALLOWED_MIME_TYPES = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "application/pdf": ".pdf",
    }

    @staticmethod
    def _ensure_message_access(db: Session, current_user: User, message_id: int) -> Message:
        message = db.query(Message).filter(Message.id == message_id, Message.deleted_at.is_(None)).first()
        if not message:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")

        conversation = db.query(Conversation).filter(Conversation.id == message.conversation_id).first()
        if not conversation:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

        if current_user.id not in {conversation.participant_a_id, conversation.participant_b_id}:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

        return message

    @staticmethod
    async def upload_attachment(
        db: Session,
        current_user: User,
        message_id: int,
        upload_file: UploadFile,
    ) -> MessageAttachment:
        message = AttachmentService._ensure_message_access(db, current_user, message_id)

        mime_type = (upload_file.content_type or "").lower()
        if mime_type not in AttachmentService.ALLOWED_MIME_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only image files (jpg/png/webp) and PDF are allowed",
            )

        file_bytes = await upload_file.read()
        if not file_bytes:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file")

        if len(file_bytes) > AttachmentService.MAX_FILE_SIZE:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File is too large")

        extension = AttachmentService.ALLOWED_MIME_TYPES[mime_type]
        safe_name = f"{uuid4().hex}{extension}"

        upload_dir = Path(UPLOADS_DIR) / "messages"
        upload_dir.mkdir(parents=True, exist_ok=True)
        destination = upload_dir / safe_name
        destination.write_bytes(file_bytes)

        file_url = f"/uploads/messages/{safe_name}"
        attachment = MessageAttachment(
            message_id=message.id,
            file_name=safe_name,
            mime_type=mime_type,
            file_size=len(file_bytes),
            file_url=file_url,
        )
        db.add(attachment)

        message.message_type = "image" if mime_type.startswith("image/") else "file"

        db.commit()
        db.refresh(attachment)
        return attachment

    @staticmethod
    def get_attachment(db: Session, current_user: User, attachment_id: int) -> MessageAttachment:
        attachment = db.query(MessageAttachment).filter(MessageAttachment.id == attachment_id).first()
        if not attachment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment not found")

        AttachmentService._ensure_message_access(db, current_user, attachment.message_id)
        return attachment
