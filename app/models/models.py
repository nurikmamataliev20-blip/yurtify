from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import (
    String, Integer, Float, Boolean, DateTime, ForeignKey, 
    Text, UniqueConstraint, Index, func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    token: Mapped[str] = mapped_column(String(512), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="refresh_tokens")

class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    full_name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    phone: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    profile_image_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    bio: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    city: Mapped[str] = mapped_column(String(100), index=True)
    preferred_language: Mapped[str] = mapped_column(String(10), default="en")
    account_status: Mapped[str] = mapped_column(String(50), default="active") # active, suspended, deleted
    role: Mapped[str] = mapped_column(String(50), default="user")

    listings: Mapped[List["Listing"]] = relationship(back_populates="owner")
    favorites: Mapped[List["Favorite"]] = relationship(back_populates="user")
    notifications: Mapped[List["Notification"]] = relationship(back_populates="user")
    payments: Mapped[List["Payment"]] = relationship(back_populates="user")
    promotions: Mapped[List["Promotion"]] = relationship(back_populates="user")
    sent_reports: Mapped[List["Report"]] = relationship("Report", foreign_keys="Report.reporter_user_id", back_populates="reporter")
    handled_reports: Mapped[List["Report"]] = relationship("Report", foreign_keys="Report.reviewed_by_admin_id", back_populates="reviewer")
    refresh_tokens: Mapped[List["RefreshToken"]] = relationship(back_populates="user", cascade="all, delete-orphan")

class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(255), unique=True)
    parent_category_id: Mapped[Optional[int]] = mapped_column(ForeignKey("categories.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    display_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    listings: Mapped[List["Listing"]] = relationship(back_populates="category")
    subcategories: Mapped[List["Category"]] = relationship("Category", back_populates="parent_category", foreign_keys=[parent_category_id])
    parent_category: Mapped[Optional["Category"]] = relationship("Category", back_populates="subcategories", foreign_keys=[parent_category_id], remote_side=[id])

class Listing(Base, TimestampMixin):
    __tablename__ = "listings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    price: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(10), default="USD")
    city: Mapped[str] = mapped_column(String(100), index=True)
    status: Mapped[str] = mapped_column(String(50), default="draft", index=True) # draft, published, sold, archived
    condition: Mapped[str] = mapped_column(String(50)) # new, used
    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    is_negotiable: Mapped[bool] = mapped_column(Boolean, default=False)
    view_count: Mapped[int] = mapped_column(Integer, default=0)
    moderation_status: Mapped[str] = mapped_column(String(50), default="pending")
    promotion_status: Mapped[str] = mapped_column(String(50), default="none")
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    owner: Mapped["User"] = relationship(back_populates="listings")
    category: Mapped["Category"] = relationship(back_populates="listings")
    images: Mapped[List["ListingImage"]] = relationship(back_populates="listing")
    favorites: Mapped[List["Favorite"]] = relationship(back_populates="listing")
    conversations: Mapped[List["Conversation"]] = relationship(back_populates="listing")
    payments: Mapped[List["Payment"]] = relationship(back_populates="listing")
    promotions: Mapped[List["Promotion"]] = relationship(back_populates="listing")

class ListingImage(Base):
    __tablename__ = "listing_images"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id"))
    file_url: Mapped[str] = mapped_column(String(512))
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    listing: Mapped["Listing"] = relationship(back_populates="images")

class Favorite(Base):
    __tablename__ = "favorites"
    __table_args__ = (
        UniqueConstraint("user_id", "listing_id", name="uix_user_listing_favorite"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="favorites")
    listing: Mapped["Listing"] = relationship(back_populates="favorites")

class Conversation(Base):
    __tablename__ = "conversations"
    __table_args__ = (
        UniqueConstraint("listing_id", "participant_a_id", "participant_b_id", name="uix_conversation_listing_participants"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id"))
    participant_a_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    participant_b_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    last_message_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    listing: Mapped["Listing"] = relationship(back_populates="conversations")
    messages: Mapped[List["Message"]] = relationship(back_populates="conversation")
    participant_a: Mapped["User"] = relationship("User", foreign_keys=[participant_a_id])
    participant_b: Mapped["User"] = relationship("User", foreign_keys=[participant_b_id])

class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id"))
    sender_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    message_type: Mapped[str] = mapped_column(String(50), default="text") # text, image, file
    text_body: Mapped[str] = mapped_column(Text)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    sent_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")
    attachments: Mapped[List["MessageAttachment"]] = relationship(back_populates="message")
    sender: Mapped["User"] = relationship("User")

class MessageAttachment(Base):
    __tablename__ = "message_attachments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    message_id: Mapped[int] = mapped_column(ForeignKey("messages.id"))
    file_name: Mapped[str] = mapped_column(String(255))
    mime_type: Mapped[str] = mapped_column(String(100))
    file_size: Mapped[int] = mapped_column(Integer)
    file_url: Mapped[str] = mapped_column(String(512))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    message: Mapped["Message"] = relationship(back_populates="attachments")

class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    type: Mapped[str] = mapped_column(String(50))
    title: Mapped[str] = mapped_column(String(255))
    body: Mapped[str] = mapped_column(Text)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)

    user: Mapped["User"] = relationship(back_populates="notifications")

class Report(Base):
    __tablename__ = "reports"
    __table_args__ = (
        Index("ix_reports_target_type_target_id", "target_type", "target_id"),
        Index("ix_reports_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    reporter_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    target_type: Mapped[str] = mapped_column(String(50)) # listing, user, message
    target_id: Mapped[int] = mapped_column(Integer)
    reason_code: Mapped[str] = mapped_column(String(50))
    reason_text: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(50), default="pending") # pending, reviewed, resolved
    resolution_note: Mapped[Optional[str]] = mapped_column(Text)
    reviewed_by_admin_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    reporter: Mapped["User"] = relationship("User", foreign_keys=[reporter_user_id], back_populates="sent_reports")
    reviewer: Mapped[Optional["User"]] = relationship("User", foreign_keys=[reviewed_by_admin_id], back_populates="handled_reports")

class Payment(Base, TimestampMixin):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    listing_id: Mapped[Optional[int]] = mapped_column(ForeignKey("listings.id"))
    promotion_id: Mapped[Optional[int]] = mapped_column(ForeignKey("promotions.id"))
    amount: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(10), default="USD")
    status: Mapped[str] = mapped_column(String(50), default="pending", index=True) # pending, completed, failed, refunded
    payment_provider: Mapped[str] = mapped_column(String(100))
    provider_reference: Mapped[Optional[str]] = mapped_column(String(255))
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    user: Mapped["User"] = relationship(back_populates="payments")
    listing: Mapped[Optional["Listing"]] = relationship(back_populates="payments")
    promotion: Mapped[Optional["Promotion"]] = relationship(back_populates="payments")

class Promotion(Base):
    __tablename__ = "promotions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    promotion_type: Mapped[str] = mapped_column(String(50)) # top, highlight, vip
    target_city: Mapped[Optional[str]] = mapped_column(String(100))
    target_category_id: Mapped[Optional[int]] = mapped_column(ForeignKey("categories.id"))
    starts_at: Mapped[datetime] = mapped_column(DateTime)
    ends_at: Mapped[datetime] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(50), default="active", index=True) # active, expired, cancelled
    purchased_price: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="promotions")
    listing: Mapped["Listing"] = relationship(back_populates="promotions")
    payments: Mapped[List["Payment"]] = relationship(back_populates="promotion")

class PromotionPackage(Base):
    __tablename__ = "promotion_packages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    price: Mapped[float] = mapped_column(Float)
    duration_days: Mapped[int] = mapped_column(Integer)
    promotion_type: Mapped[str] = mapped_column(String(50))
    description: Mapped[Optional[str]] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

class AdminAuditLog(Base):
    __tablename__ = "admin_audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    admin_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(255))
    target_type: Mapped[str] = mapped_column(String(50))
    target_id: Mapped[int] = mapped_column(Integer)
    note: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    admin: Mapped["User"] = relationship("User")
