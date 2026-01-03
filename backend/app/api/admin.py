"""
Admin API Endpoints

Provides user management, channel management, and audio administration endpoints.
Only accessible by admin users.
"""

from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from uuid import UUID
import logging

from app.db.session import get_db
from app.models.user import User
from app.models.channel import Channel, ChannelMembership, TranscriptionChannel
from app.models.transcription import Transcription
from app.schemas.admin import (
    UserResponse, UserAdminToggleRequest,
    ChannelCreate, ChannelUpdate, ChannelResponse, ChannelDetailResponse,
    ChannelMemberResponse, ChannelAssignmentRequest,
    TranscriptionChannelAssignmentRequest, AdminTranscriptionResponse,
    AdminTranscriptionListResponse
)
from app.api.deps import require_admin, require_active

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


# ========================================
# User Management Endpoints
# ========================================

@router.get("/users", response_model=List[UserResponse])
def list_users(
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin)
):
    """
    List all users (admin only).

    Returns all non-deleted users with their activation and admin status.
    """
    users = db.query(User).filter(User.deleted_at.is_(None)).all()
    # Convert SQLAlchemy models to Pydantic schemas
    return [UserResponse.model_validate(u) for u in users]


@router.put("/users/{user_id}/activate", response_model=UserResponse)
def activate_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin)
):
    """
    Activate a user account (admin only).

    Sets is_active=True and records activation timestamp.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    user.is_active = True
    user.activated_at = datetime.utcnow()
    db.commit()
    db.refresh(user)

    logger.info(f"User {user.email} activated by admin {current_admin.email}")
    return UserResponse.model_validate(user)


@router.put("/users/{user_id}/admin", response_model=UserResponse)
def toggle_user_admin(
    user_id: str,
    admin_data: UserAdminToggleRequest,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin)
):
    """
    Toggle user admin status (admin only).

    Cannot modify own admin status. Prevents removing admin from last admin.
    """
    if user_id == str(current_admin.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot modify your own admin status"
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Check if this is the last admin being demoted
    if user.is_admin and not admin_data.is_admin:
        admin_count = db.query(User).filter(
            User.is_admin == True,
            User.deleted_at.is_(None)
        ).count()
        if admin_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot remove admin status from the last admin"
            )

    user.is_admin = admin_data.is_admin
    db.commit()
    db.refresh(user)

    logger.info(
        f"User {user.email} admin status set to {admin_data.is_admin} "
        f"by admin {current_admin.email}"
    )
    return UserResponse.model_validate(user)


@router.delete("/users/{user_id}")
def delete_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin)
):
    """
    Delete user (admin only).

    Performs soft delete (sets deleted_at). Transfers ownership of transcriptions
    to the deleting admin. Cannot delete self or last admin.
    """
    if user_id == str(current_admin.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Check if this is the last admin
    if user.is_admin:
        admin_count = db.query(User).filter(
            User.is_admin == True,
            User.deleted_at.is_(None)
        ).count()
        if admin_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete the last admin"
            )

    # Soft delete
    user.deleted_at = datetime.utcnow()
    user.email = f"deleted_{user.id}@local"  # Uniquify email
    db.commit()

    # Transfer ownership of transcriptions to admin
    db.query(Transcription).filter(
        Transcription.user_id == user_id
    ).update({"user_id": current_admin.id})
    db.commit()

    logger.info(f"User {user.email} soft-deleted by admin {current_admin.email}")
    return {"message": "User deleted successfully"}


# ========================================
# Channel Management Endpoints
# ========================================

@router.get("/channels", response_model=List[ChannelResponse])
def list_channels(
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin)
):
    """
    List all channels (admin only).
    """
    channels = db.query(Channel).all()
    result = []
    for channel in channels:
        member_count = db.query(ChannelMembership).filter(
            ChannelMembership.channel_id == channel.id
        ).count()
        result.append(ChannelResponse(
            id=channel.id,
            name=channel.name,
            description=channel.description,
            created_by=channel.created_by,
            created_at=channel.created_at,
            updated_at=channel.updated_at,
            member_count=member_count
        ))
    return result


@router.post("/channels", response_model=ChannelResponse, status_code=status.HTTP_201_CREATED)
def create_channel(
    channel_data: ChannelCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin)
):
    """
    Create a new channel (admin only).
    """
    # Check for duplicate name
    existing = db.query(Channel).filter(Channel.name == channel_data.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Channel name already exists"
        )

    channel = Channel(
        name=channel_data.name,
        description=channel_data.description,
        created_by=current_admin.id
    )
    db.add(channel)
    db.commit()
    db.refresh(channel)

    logger.info(f"Channel '{channel.name}' created by admin {current_admin.email}")
    return ChannelResponse(
        id=channel.id,
        name=channel.name,
        description=channel.description,
        created_by=channel.created_by,
        created_at=channel.created_at,
        updated_at=channel.updated_at,
        member_count=0
    )


@router.put("/channels/{channel_id}", response_model=ChannelResponse)
def update_channel(
    channel_id: str,
    channel_data: ChannelUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin)
):
    """
    Update channel (admin only).
    """
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Channel not found"
        )

    if channel_data.name is not None:
        # Check for duplicate name (excluding current channel)
        existing = db.query(Channel).filter(
            Channel.name == channel_data.name,
            Channel.id != channel_id
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Channel name already exists"
            )
        channel.name = channel_data.name

    if channel_data.description is not None:
        channel.description = channel_data.description

    channel.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(channel)

    member_count = db.query(ChannelMembership).filter(
        ChannelMembership.channel_id == channel.id
    ).count()

    logger.info(f"Channel '{channel.name}' updated by admin {current_admin.email}")
    return ChannelResponse(
        id=channel.id,
        name=channel.name,
        description=channel.description,
        created_by=channel.created_by,
        created_at=channel.created_at,
        updated_at=channel.updated_at,
        member_count=member_count
    )


@router.delete("/channels/{channel_id}")
def delete_channel(
    channel_id: str,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin)
):
    """
    Delete channel (admin only).

    Cascades to channel memberships and transcription assignments.
    """
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Channel not found"
        )

    channel_name = channel.name
    db.delete(channel)
    db.commit()

    logger.info(f"Channel '{channel_name}' deleted by admin {current_admin.email}")
    return {"message": "Channel deleted successfully"}


@router.post("/channels/{channel_id}/members", response_model=ChannelMemberResponse)
def assign_user_to_channel(
    channel_id: str,
    assignment: ChannelAssignmentRequest,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin)
):
    """
    Assign a user to a channel (admin only).
    """
    # Verify channel exists
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Channel not found"
        )

    # Verify user exists
    user = db.query(User).filter(
        User.id == str(assignment.user_id),
        User.deleted_at.is_(None)
    ).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Check for existing membership
    existing = db.query(ChannelMembership).filter(
        ChannelMembership.channel_id == channel_id,
        ChannelMembership.user_id == str(assignment.user_id)
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already assigned to this channel"
        )

    membership = ChannelMembership(
        channel_id=channel_id,
        user_id=str(assignment.user_id),
        assigned_by=current_admin.id
    )
    db.add(membership)
    db.commit()
    db.refresh(membership)

    logger.info(
        f"User {user.email} assigned to channel '{channel.name}' "
        f"by admin {current_admin.email}"
    )
    return ChannelMemberResponse(
        channel_id=membership.channel_id,
        user_id=membership.user_id,  # Already a UUID from SQLAlchemy
        assigned_at=membership.assigned_at,
        assigned_by=membership.assigned_by  # Already a UUID from SQLAlchemy
    )


@router.delete("/channels/{channel_id}/members/{user_id}")
def remove_user_from_channel(
    channel_id: str,
    user_id: str,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin)
):
    """
    Remove a user from a channel (admin only).
    """
    membership = db.query(ChannelMembership).filter(
        ChannelMembership.channel_id == channel_id,
        ChannelMembership.user_id == user_id
    ).first()
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Channel membership not found"
        )

    db.delete(membership)
    db.commit()

    logger.info(
        f"User {user_id} removed from channel {channel_id} "
        f"by admin {current_admin.email}"
    )
    return {"message": "User removed from channel"}


@router.get("/channels/{channel_id}", response_model=ChannelDetailResponse)
def get_channel_detail(
    channel_id: str,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin)
):
    """
    Get channel detail with member list (admin only).
    """
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Channel not found"
        )

    # Get members
    memberships = db.query(ChannelMembership).filter(
        ChannelMembership.channel_id == channel_id
    ).all()

    member_ids = [m.user_id for m in memberships]
    members = db.query(User).filter(
        User.id.in_(member_ids),
        User.deleted_at.is_(None)
    ).all()

    # Convert SQLAlchemy models to Pydantic schemas
    member_responses = [UserResponse.model_validate(m) for m in members]

    return ChannelDetailResponse(
        id=channel.id,
        name=channel.name,
        description=channel.description,
        created_by=channel.created_by,
        created_at=channel.created_at,
        updated_at=channel.updated_at,
        member_count=len(members),
        members=member_responses
    )


# ========================================
# Audio Management Endpoints (Admin)
# ========================================

@router.get("/audio", response_model=AdminTranscriptionListResponse)
def list_all_audio(
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin)
):
    """
    List all audio in system (admin only).

    Admin bypasses channel filters and sees all content.
    """
    transcriptions = db.query(Transcription).filter(
        Transcription.deleted_at.is_(None) if hasattr(Transcription, 'deleted_at') else True
    ).all()

    # Handle both cases: with and without deleted_at column
    if not hasattr(Transcription, 'deleted_at'):
        transcriptions = db.query(Transcription).all()

    result = []
    for t in transcriptions:
        # Get channels for this transcription
        channel_assignments = db.query(TranscriptionChannel).filter(
            TranscriptionChannel.transcription_id == t.id
        ).all()
        channel_ids = [a.channel_id for a in channel_assignments]
        channels = db.query(Channel).filter(Channel.id.in_(channel_ids)).all()

        # Convert SQLAlchemy models to Pydantic schemas
        channel_responses = [ChannelResponse.model_validate(c) for c in channels]

        result.append(AdminTranscriptionResponse(
            id=t.id,
            user_id=t.user_id,
            file_name=t.file_name,
            language=t.language,
            duration_seconds=t.duration_seconds,
            stage=t.stage,
            error_message=t.error_message,
            pptx_status=t.pptx_status,
            created_at=t.created_at,
            completed_at=getattr(t, 'completed_at', None),
            channels=channel_responses
        ))

    return AdminTranscriptionListResponse(
        total=len(result),
        items=result
    )


@router.post("/audio/{audio_id}/channels")
def assign_audio_to_channels(
    audio_id: str,
    assignment: TranscriptionChannelAssignmentRequest,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin)
):
    """
    Assign audio to multiple channels (admin only).

    Clears existing assignments and replaces with new ones.
    """
    transcription = db.query(Transcription).filter(
        Transcription.id == audio_id
    ).first()
    if not transcription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audio not found"
        )

    # Verify all channels exist
    channel_ids = [str(cid) for cid in assignment.channel_ids]
    channels = db.query(Channel).filter(Channel.id.in_(channel_ids)).all()
    if len(channels) != len(channel_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="One or more channels not found"
        )

    # Remove existing assignments
    db.query(TranscriptionChannel).filter(
        TranscriptionChannel.transcription_id == audio_id
    ).delete()

    # Add new assignments
    for channel_id in channel_ids:
        ta = TranscriptionChannel(
            transcription_id=audio_id,
            channel_id=channel_id,
            assigned_by=current_admin.id
        )
        db.add(ta)

    db.commit()

    logger.info(
        f"Audio {audio_id} assigned to {len(channel_ids)} channels "
        f"by admin {current_admin.email}"
    )
    return {
        "message": f"Assigned to {len(channel_ids)} channels",
        "channel_ids": channel_ids
    }


@router.get("/audio/{audio_id}/channels", response_model=List[ChannelResponse])
def get_audio_channels(
    audio_id: str,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin)
):
    """
    Get channels assigned to audio (admin only).
    """
    # Verify transcription exists
    transcription = db.query(Transcription).filter(
        Transcription.id == audio_id
    ).first()
    if not transcription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audio not found"
        )

    # Get channel assignments
    assignments = db.query(TranscriptionChannel).filter(
        TranscriptionChannel.transcription_id == audio_id
    ).all()

    channel_ids = [a.channel_id for a in assignments]
    channels = db.query(Channel).filter(Channel.id.in_(channel_ids)).all()

    # Convert SQLAlchemy models to Pydantic schemas
    return [ChannelResponse.model_validate(c) for c in channels]
