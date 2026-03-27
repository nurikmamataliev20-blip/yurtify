from datetime import datetime
from typing import List, Literal, Optional

from pydantic import AliasChoices, BaseModel, Field, model_validator


class ConversationStartRequest(BaseModel):
    listing_id: int = Field(..., ge=1)
    recipient_user_id: int = Field(
        ...,
        ge=1,
        validation_alias=AliasChoices("recipient_user_id", "recipient_id"),
    )


class ConversationRead(BaseModel):
    id: int
    listing_id: int
    participant_a_id: int
    participant_b_id: int
    last_message_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class PaginatedConversations(BaseModel):
    page: int
    page_size: int
    total_items: int
    total_pages: int
    items: List[ConversationRead]


class MessageAttachmentRead(BaseModel):
    id: int
    message_id: int
    file_name: str
    mime_type: str
    file_size: int
    file_url: str
    created_at: datetime

    class Config:
        from_attributes = True


class MessageCreate(BaseModel):
    conversation_id: int = Field(..., ge=1)
    message_type: Literal["text", "image", "file"] = "text"
    text_body: Optional[str] = None
    attachment_id: Optional[int] = Field(default=None, ge=1)
    attachment_ids: List[int] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_text_payload(self):
        if self.message_type == "text" and not (self.text_body and self.text_body.strip()):
            raise ValueError("text_body is required for text messages")
        if self.attachment_id is not None and self.attachment_id in self.attachment_ids:
            raise ValueError("attachment_id must not be duplicated in attachment_ids")
        return self


class MessageRead(BaseModel):
    id: int
    conversation_id: int
    sender_id: int
    message_type: str
    text_body: str
    is_read: bool
    sent_at: datetime
    deleted_at: Optional[datetime] = None
    attachments: List[MessageAttachmentRead] = []

    class Config:
        from_attributes = True


class PaginatedMessages(BaseModel):
    page: int
    page_size: int
    total_items: int
    total_pages: int
    items: List[MessageRead]


class AttachmentUploadResponse(BaseModel):
    id: int
    message_id: int
    file_name: str
    mime_type: str
    file_size: int
    file_url: str
    created_at: datetime

    class Config:
        from_attributes = True
