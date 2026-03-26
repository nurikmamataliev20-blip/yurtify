from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.models import User, RefreshToken
from app.schemas.user_schemas import (
    UserCreate, LoginRequest, Token, 
    ChangePasswordRequest, ResetPasswordRequest
)
from app.core.security import (
    get_password_hash, verify_password, 
    create_access_token, create_refresh_token, create_reset_token,
    verify_token
)
from app.core.config import settings

class AuthService:
    @staticmethod
    def register_user(db: Session, user_in: UserCreate) -> User:
        # Check if user already exists
        if db.query(User).filter(User.email == user_in.email).first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A user with this email already exists"
            )
        if db.query(User).filter(User.phone == user_in.phone).first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A user with this phone number already exists"
            )
        
        # Hash password and create user
        hashed_password = get_password_hash(user_in.password)
        db_user = User(
            full_name=user_in.full_name,
            email=user_in.email,
            phone=user_in.phone,
            hashed_password=hashed_password,
            city=user_in.city,
            preferred_language=user_in.preferred_language,
            account_status="active"
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user

    @staticmethod
    def login(db: Session, login_data: LoginRequest) -> Token:
        user = db.query(User).filter(User.email == login_data.email).first()
        if not user or not verify_password(login_data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if user.account_status != "active":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Account is {user.account_status}"
            )

        # Create tokens
        access_token = create_access_token(data={"sub": user.email})
        refresh_token_str = create_refresh_token(data={"sub": user.email})
        
        # Save refresh token in DB
        refresh_expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        db_refresh = RefreshToken(
            user_id=user.id,
            token=refresh_token_str,
            expires_at=refresh_expire
        )
        db.add(db_refresh)
        db.commit()

        return Token(
            access_token=access_token,
            refresh_token=refresh_token_str
        )

    @staticmethod
    def logout(db: Session, token: str):
        db_refresh = db.query(RefreshToken).filter(RefreshToken.token == token).first()
        if db_refresh:
            db.delete(db_refresh)
            db.commit()

    @staticmethod
    def refresh_access_token(db: Session, refresh_token: str) -> Token:
        # Verify token cryptographically
        payload = verify_token(refresh_token, "refresh")
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        # Verify token in DB
        db_token = db.query(RefreshToken).filter(RefreshToken.token == refresh_token).first()
        if not db_token or db_token.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
            if db_token:
                db.delete(db_token)
                db.commit()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token expired or invalid"
            )
        
        user = db_token.user
        if user.account_status != "active":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Account is {user.account_status}"
            )

        # Create new access token
        access_token = create_access_token(data={"sub": user.email})
        
        return Token(
            access_token=access_token,
            refresh_token=refresh_token
        )

    @staticmethod
    def forgot_password(db: Session, email: str) -> str:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Create a reset token
        reset_token = create_reset_token(data={"sub": user.email})
        return reset_token

    @staticmethod
    def reset_password(db: Session, reset_data: ResetPasswordRequest):
        payload = verify_token(reset_data.token, "reset")
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token"
            )
        
        email = payload.get("sub")
        user = db.query(User).filter(User.email == email).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        
        user.hashed_password = get_password_hash(reset_data.new_password)
        db.query(RefreshToken).filter(RefreshToken.user_id == user.id).delete()
        db.commit()

    @staticmethod
    def change_password(db: Session, current_user: User, pass_data: ChangePasswordRequest):
        if not verify_password(pass_data.current_password, current_user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Incorrect current password"
            )
        
        current_user.hashed_password = get_password_hash(pass_data.new_password)
        db.commit()
