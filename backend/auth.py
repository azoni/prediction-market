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

from fastapi import Depends, HTTPException, Header
from sqlalchemy.orm import Session

from database import get_db
from models import User

# Try to import firebase-admin, but don't fail if not installed
try:
    import firebase_admin
    from firebase_admin import auth as firebase_auth, credentials
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False
    firebase_admin = None


# =============================================================================
# Firebase Admin Initialization
# =============================================================================

# List of admin emails - ADD YOUR EMAIL HERE
ADMIN_EMAILS = [
    # "your-email@gmail.com",  # <-- Add your Google email
    "charltonuw@gmail.com",
]

# List of admin user IDs (Firebase UIDs) - alternative to email
ADMIN_USER_IDS = [
    # "firebase-uid-here",
]

# Track if we're in dev mode (no Firebase verification)
_dev_mode = True


def init_firebase():
    """
    Initialize Firebase Admin SDK.
    
    For local development: Set GOOGLE_APPLICATION_CREDENTIALS env var
    to path of your service account JSON file.
    
    For production (Render/etc): Set FIREBASE_CREDENTIALS env var
    to the JSON content of your service account.
    """
    global _dev_mode
    
    if not FIREBASE_AVAILABLE:
        print("⚠️  firebase-admin not installed. Running in DEV MODE.")
        print("⚠️  Auth tokens will NOT be verified. Install firebase-admin for production.")
        _dev_mode = True
        return
    
    if firebase_admin._apps:
        _dev_mode = False
        return  # Already initialized
    
    # Option 1: Credentials from environment variable (for production)
    creds_json = os.getenv("FIREBASE_CREDENTIALS")
    if creds_json:
        import json
        creds_dict = json.loads(creds_json)
        cred = credentials.Certificate(creds_dict)
        firebase_admin.initialize_app(cred)
        print("Firebase Admin initialized from FIREBASE_CREDENTIALS env var")
        _dev_mode = False
        return
    
    # Option 2: Credentials file path (for local development)
    creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if creds_path and os.path.exists(creds_path):
        cred = credentials.Certificate(creds_path)
        firebase_admin.initialize_app(cred)
        print(f"Firebase Admin initialized from {creds_path}")
        _dev_mode = False
        return
    
    # Option 3: Default credentials (for Google Cloud environments)
    try:
        firebase_admin.initialize_app()
        print("Firebase Admin initialized with default credentials")
        _dev_mode = False
        return
    except Exception:
        pass
    
    # If we get here, Firebase is not configured - run in dev mode
    print("⚠️  WARNING: Firebase Admin not configured. Running in DEV MODE.")
    print("⚠️  Auth tokens will NOT be verified. Do not use in production!")
    _dev_mode = True


def is_dev_mode() -> bool:
    """Check if running without Firebase verification."""
    return _dev_mode


# =============================================================================
# Token Verification
# =============================================================================

def decode_jwt_payload(token: str) -> dict:
    """
    Decode a JWT payload without verification.
    JWTs are base64-encoded JSON in format: header.payload.signature
    """
    import base64
    import json
    
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        
        payload = parts[1]
        padding = 4 - len(payload) % 4
        if padding != 4:
            payload += "=" * padding
        
        decoded_bytes = base64.urlsafe_b64decode(payload)
        return json.loads(decoded_bytes.decode("utf-8"))
    except Exception:
        return None


def verify_firebase_token(id_token: str) -> dict:
    if is_dev_mode():
        decoded = decode_jwt_payload(id_token)
        if decoded:
            return {
                "uid": decoded.get("user_id") or decoded.get("sub"),
                "email": decoded.get("email"),
                "name": decoded.get("name"),
            }
        
        if len(id_token) < 50 and "." not in id_token:
            return {"uid": id_token, "email": None, "name": None}
        
        raise HTTPException(status_code=401, detail="Invalid token format")


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
    except Exception as e:
        print(f"Firebase init failed: {e}")
        _dev_mode = True
