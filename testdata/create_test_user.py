#!/usr/bin/env python3
"""Create test user in database."""
import sys
sys.path.insert(0, '/home/lmr/ws/whisper_summarizer/backend')

from app.db.session import SessionLocal
from app.models.user import User

# Test user ID from DISABLE_AUTH mode
TEST_USER_ID = "123e4567-e89b-12d3-a456-426614174000"
TEST_EMAIL = "test@example.com"

def create_test_user():
    """Create test user if not exists."""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == TEST_USER_ID).first()
        if user:
            print(f"Test user already exists: {user.id} ({user.email})")
        else:
            user = User(id=TEST_USER_ID, email=TEST_EMAIL)
            db.add(user)
            db.commit()
            db.refresh(user)
            print(f"Created test user: {user.id} ({user.email})")
        return user
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    create_test_user()
