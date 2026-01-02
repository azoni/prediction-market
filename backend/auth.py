"""
Authentication & Authorization Module

Handles:
1. Firebase ID token verification (not just trusting client-sent UIDs)
2. Admin role checking
3. User session management

Security: NEVER trust client-sent user IDs. Always verify the Firebase JWT.
"""

import os
from typing import Optional
from functools import lru_cache

import firebase_admin
from firebase_admin import auth as firebase_auth, credentials
from fastapi import Depends, HTTPException, Header
from sqlalchemy.orm import Session

from database import get_db
from models import User


# =============================================================================
# Firebase Admin Initialization
# =============================================================================

# List of admin emails - ADD YOUR EMAIL HERE
ADMIN_EMAILS = [
    "charltonuw@gmail.com",
    # "your-email@gmail.com",  # <-- Add your Google email
]

# List of admin user IDs (Firebase UIDs) - alternative to email
ADMIN_USER_IDS = [
    # "firebase-uid-here",
]


def init_firebase():
    """
    Initialize Firebase Admin SDK.
    
    For local development: Set GOOGLE_APPLICATION_CREDENTIALS env var
    to path of your service account JSON file.
    
    For production (Render/etc): Set FIREBASE_CREDENTIALS env var
    to the JSON content of your service account.
    """
    if firebase_admin._apps:
        return  # Already initialized
    
    # Option 1: Credentials from environment variable (for production)
    creds_json = os.getenv("FIREBASE_CREDENTIALS")
    if creds_json:
        import json
        creds_dict = json.loads(creds_json)
        cred = credentials.Certificate(creds_dict)
        firebase_admin.initialize_app(cred)
        print("Firebase Admin initialized from FIREBASE_CREDENTIALS env var")
        return
    
    # Option 2: Credentials file path (for local development)
    creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if creds_path and os.path.exists(creds_path):
        cred = credentials.Certificate(creds_path)
        firebase_admin.initialize_app(cred)
        print(f"Firebase Admin initialized from {creds_path}")
        return
    
    # Option 3: Default credentials (for Google Cloud environments)
    try:
        firebase_admin.initialize_app()
        print("Firebase Admin initialized with default credentials")
        return
    except Exception:
        pass
    
    # If we get here, Firebase is not configured - run in dev mode
    print("⚠️  WARNING: Firebase Admin not configured. Running in DEV MODE.")
    print("⚠️  Auth tokens will NOT be verified. Do not use in production!")


# Track if we're in dev mode (no Firebase verification)
_dev_mode = False


def is_dev_mode() -> bool:
    """Check if running without Firebase verification."""
    return _dev_mode or not firebase_admin._apps


# =============================================================================
# Token Verification
# =============================================================================

def verify_firebase_token(id_token: str) -> dict:
    """
    Verify a Firebase ID token and return the decoded claims.
    
    Returns dict with: uid, email, name, picture, etc.
    Raises HTTPException if token is invalid.
    """
    if is_dev_mode():
        # In dev mode, the "token" is just the UID
        # This is insecure but allows testing without Firebase setup
        return {
            "uid": id_token,
            "email": None,
            "name": None,
        }
    
    try:
        decoded = firebase_auth.verify_id_token(id_token)
        return decoded
    except firebase_auth.InvalidIdTokenError:
        raise HTTPException(status_code=401, detail="Invalid authentication token")
    except firebase_auth.ExpiredIdTokenError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except firebase_auth.RevokedIdTokenError:
        raise HTTPException(status_code=401, detail="Token has been revoked")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")


# =============================================================================
# Authorization Helpers
# =============================================================================

def is_admin(user: User) -> bool:
    """Check if a user has admin privileges."""
    # Check by user ID
    if user.id in ADMIN_USER_IDS:
        return True
    
    # Check by email
    if user.email and user.email.lower() in [e.lower() for e in ADMIN_EMAILS]:
        return True
    
    # Check database flag (if we add one later)
    if hasattr(user, 'is_admin') and user.is_admin:
        return True
    
    return False


def require_admin(user: User) -> None:
    """Raise 403 if user is not an admin."""
    if not is_admin(user):
        raise HTTPException(
            status_code=403,
            detail="Admin privileges required"
        )


# =============================================================================
# FastAPI Dependencies
# =============================================================================

async def get_current_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> User:
    """
    FastAPI dependency to get the authenticated user.
    
    Verifies the Firebase ID token from the Authorization header
    and returns the corresponding User from our database.
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")
    
    # Parse "Bearer <token>" format
    try:
        scheme, token = authorization.split(" ", 1)
        if scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="Invalid auth scheme. Use 'Bearer <token>'")
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid authorization header format")
    
    # Verify the token
    claims = verify_firebase_token(token)
    user_id = claims["uid"]
    
    # Get user from database
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found. Please register first.")
    
    return user


async def get_current_admin(
    user: User = Depends(get_current_user),
) -> User:
    """
    FastAPI dependency to get an authenticated admin user.
    
    Raises 403 if the user is not an admin.
    """
    require_admin(user)
    return user


async def get_optional_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """
    FastAPI dependency that returns the user if authenticated, None otherwise.
    
    Use this for endpoints that work for both authenticated and anonymous users.
    """
    if not authorization:
        return None
    
    try:
        return await get_current_user(authorization, db)
    except HTTPException:
        return None


# =============================================================================
# Initialization
# =============================================================================

def setup_auth():
    """Call this on app startup to initialize Firebase."""
    global _dev_mode
    try:
        init_firebase()
        _dev_mode = not firebase_admin._apps
    except Exception as e:
        print(f"Firebase init failed: {e}")
        _dev_mode = True
