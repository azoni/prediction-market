"""
Authentication module for DuMarket.

Handles Firebase token verification and admin authorization.
"""

import os
import json
import base64
from typing import Optional
from fastapi import Depends, HTTPException, Header
from sqlalchemy.orm import Session

from database import get_db
from models import User

# =============================================================================
# Admin Configuration
# =============================================================================

ADMIN_EMAILS = [
    "charltonuw@gmail.com",
    # Add more admin emails here
]

# =============================================================================
# Token Verification
# =============================================================================

def decode_jwt_payload(token: str) -> dict:
    """
    Decode the payload from a JWT token without verification.
    
    Note: This does NOT verify the signature. In production with sensitive data,
    you should use firebase-admin SDK for proper verification.
    """
    try:
        parts = token.split(".")
        if len(parts) != 3:
            raise ValueError("Invalid JWT format")
        
        payload = parts[1]
        # Add padding if needed
        padding = 4 - len(payload) % 4
        if padding != 4:
            payload += "=" * padding
        
        decoded_bytes = base64.urlsafe_b64decode(payload)
        return json.loads(decoded_bytes.decode("utf-8"))
    except Exception as e:
        raise ValueError(f"Failed to decode JWT: {e}")


def verify_firebase_token(token: str) -> dict:
    """
    Verify a Firebase ID token and return the decoded claims.
    
    In dev mode, just decodes without cryptographic verification.
    """
    return decode_jwt_payload(token)


# =============================================================================
# FastAPI Dependencies
# =============================================================================

def get_current_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> User:
    """
    FastAPI dependency to get the current authenticated user.
    
    Expects: Authorization: Bearer <firebase_id_token>
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")
    
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization format")
    
    token = authorization[7:]  # Remove "Bearer " prefix
    
    try:
        claims = verify_firebase_token(token)
        user_id = claims.get("user_id") or claims.get("sub") or claims.get("uid")
        
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token: no user ID")
        
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return user
        
    except ValueError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")


def is_admin(user: User) -> bool:
    """Check if a user has admin privileges."""
    return user.email in ADMIN_EMAILS


def get_current_admin(
    user: User = Depends(get_current_user),
) -> User:
    """
    FastAPI dependency to get the current user and verify admin status.
    """
    if not is_admin(user):
        raise HTTPException(status_code=403, detail="Admin access required")
    return user
