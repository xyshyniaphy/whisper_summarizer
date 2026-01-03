"""
API Dependencies

Provides database sessions, authentication, and permission decorators.
"""

from typing import Generator, Optional
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.user import User
from app.core.supabase import get_current_user as supabase_get_current_user


def get_db() -> Generator:
    """Get database session."""
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()


async def get_current_db_user(
    current_user: dict = Depends(supabase_get_current_user),
    db: Session = Depends(get_db)
) -> User:
    """
    Get current user from local database (synced with Supabase by email).

    Args:
        current_user: Supabase authenticated user dict
        db: Database session

    Returns:
        User: Local database User model

    Raises:
        HTTPException: User not found in local database
    """
    user = db.query(User).filter(
        User.email == current_user["email"],
        User.deleted_at.is_(None)
    ).first()

    if not user:
        # Auto-create user if not exists (for new OAuth logins)
        user = User(
            email=current_user["email"],
            is_active=False,  # Inactive by default, requires admin activation
            is_admin=False
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    return user


async def require_admin(
    current_db_user: User = Depends(get_current_db_user)
) -> User:
    """
    Require admin role for endpoint access.

    Args:
        current_db_user: Current authenticated user from local database

    Returns:
        User: The admin user

    Raises:
        HTTPException: User is not admin
    """
    if not current_db_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_db_user


async def require_active(
    current_db_user: User = Depends(get_current_db_user)
) -> User:
    """
    Require active account for endpoint access.

    Args:
        current_db_user: Current authenticated user from local database

    Returns:
        User: The active user

    Raises:
        HTTPException: User account is not activated
    """
    if not current_db_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "account_inactive",
                "message": "Your account is pending activation. Please contact an administrator.",
                "user_id": str(current_db_user.id)
            }
        )
    return current_db_user
