from pydantic import BaseModel, EmailStr, validator
from typing import Optional, List
from datetime import datetime

class UserBase(BaseModel):
    full_name: str
    email: EmailStr
    phone: str
    city: str
    preferred_language: str = "en"

class UserCreate(UserBase):
    password: str
    confirm_password: str

    @validator("confirm_password")
    def passwords_match(cls, v, values, **kwargs):
        if "password" in values and v != values["password"]:
            raise ValueError("passwords do not match")
        return v

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    bio: Optional[str] = None
    profile_image_url: Optional[str] = None
    city: Optional[str] = None
    preferred_language: Optional[str] = None

class UserRead(UserBase):
    id: int
    account_status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserMeUpdate(BaseModel):
    full_name: Optional[str] = None
    bio: Optional[str] = None
    city: Optional[str] = None
    phone: Optional[str] = None
    preferred_language: Optional[str] = None


class UserPublicProfile(BaseModel):
    id: int
    full_name: str
    city: str
    joined_at: datetime
    active_listings_count: int


class PaginatedUserListings(BaseModel):
    page: int
    page_size: int
    total_items: int
    total_pages: int
    items: List["ListingReadCompact"]


class ListingReadCompact(BaseModel):
    id: int
    title: str
    price: float
    currency: str
    city: str
    condition: str
    status: str
    moderation_status: str
    created_at: datetime

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    email: Optional[str] = None

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str
    confirm_password: str

    @validator("confirm_password")
    def passwords_match(cls, v, values, **kwargs):
        if "new_password" in values and v != values["new_password"]:
            raise ValueError("passwords do not match")
        return v

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str
    confirm_password: str

    @validator("confirm_password")
    def passwords_match(cls, v, values, **kwargs):
        if "new_password" in values and v != values["new_password"]:
            raise ValueError("passwords do not match")
        return v
