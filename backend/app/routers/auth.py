from fastapi import APIRouter, Depends, status, Body
from sqlalchemy.orm import Session
from typing import Annotated

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.schemas.user_schemas import (
    UserCreate, UserRead, LoginRequest, Token, 
    ForgotPasswordRequest, ResetPasswordRequest, ChangePasswordRequest
)
from app.services.auth_service import AuthService
from app.models.models import User

router = APIRouter()

@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    """Register a new user."""
    return AuthService.register_user(db, user_in)

@router.post("/login", response_model=Token)
def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    """Login with email and password."""
    return AuthService.login(db, login_data)

@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(token_data: Annotated[str, Body(embed=True, alias="refresh_token")], db: Session = Depends(get_db)):
    """Logout and invalidate the refresh token."""
    AuthService.logout(db, token_data)
    return None

@router.post("/refresh", response_model=Token)
def refresh(token_data: Annotated[str, Body(embed=True, alias="refresh_token")], db: Session = Depends(get_db)):
    """Refresh access token using a refresh token."""
    return AuthService.refresh_access_token(db, token_data)

@router.post("/forgot-password")
def forgot_password(request: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """Generate a password reset token."""
    token = AuthService.forgot_password(db, request.email)
    return {"reset_token": token, "message": "Password reset token generated successfully"}

@router.post("/reset-password", status_code=status.HTTP_200_OK)
def reset_password(reset_data: ResetPasswordRequest, db: Session = Depends(get_db)):
    """Reset password using a token."""
    AuthService.reset_password(db, reset_data)
    return {"message": "Password reset successfully"}

@router.post("/change-password", status_code=status.HTTP_200_OK)
def change_password(
    pass_data: ChangePasswordRequest, 
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """Change password for the logged-in user."""
    AuthService.change_password(db, current_user, pass_data)
    return {"message": "Password changed successfully"}
