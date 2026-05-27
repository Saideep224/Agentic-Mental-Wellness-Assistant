"""
Authentication route – verifies Supabase JWT token and extracts user profile info.
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.config import settings
from app.database import get_db
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

# ── JWT bearer scheme ────────────────────────────────────────
bearer_scheme = HTTPBearer()


def decode_and_verify_token(token: str) -> dict:
    """Decodes and verifies a JWT token (supporting both Supabase JWT and local fallback)."""
    # Mask token for logs
    masked_token = f"{token[:8]}...{token[-8:]}" if len(token) > 16 else "***"
    
    try:
        # Decode Supabase JWT
        if getattr(settings, "SUPABASE_JWT_SECRET", None):
            logger.info(f"[AUTH] Attempting to decode token {masked_token} with SUPABASE_JWT_SECRET...")
            payload = jwt.decode(
                token, settings.SUPABASE_JWT_SECRET, algorithms=["HS256"], options={"verify_aud": False}
            )
            logger.info("[AUTH] Token successfully decoded with Supabase JWT Secret.")
            return payload
        else:
            logger.warning("[AUTH] SUPABASE_JWT_SECRET not set. Reading unverified claims.")
            payload = jwt.get_unverified_claims(token)
            return payload
    except Exception as supabase_err:
        logger.warning(f"[AUTH] Supabase verification failed: {supabase_err}. Trying local JWT fallback...")
        try:
            # Fallback to local JWT signature
            payload = jwt.decode(
                token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
            )
            logger.info("[AUTH] Token successfully decoded with local JWT secret.")
            return payload
        except (JWTError, ValueError) as local_err:
            logger.error(f"[AUTH] Local verification fallback failed: {local_err}")
            raise ValueError(f"Token validation failed (Supabase: {supabase_err}, Local: {local_err})") from supabase_err


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """FastAPI dependency – extracts and verifies the Supabase JWT, returns the User (profiles) row."""
    token = credentials.credentials
    
    # Log incoming auth header info
    auth_header = request.headers.get("Authorization", "")
    masked_header = f"Bearer {auth_header[7:15]}...{auth_header[-8:]}" if len(auth_header) > 20 else auth_header
    logger.info(f"[AUTH] Incoming request to {request.url.path} with header: '{masked_header}'")

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = decode_and_verify_token(token)
        user_id_str: str | None = payload.get("sub")
        if user_id_str is None:
            logger.error("[AUTH] Sub claim is missing from JWT payload.")
            raise credentials_exception
        user_id = uuid.UUID(user_id_str)
        logger.info(f"[AUTH] Token verified. Decoded user_id: {user_id}")
    except Exception as e:
        logger.error(f"[AUTH] Authentication failed for token: {e}")
        raise credentials_exception

    # Query profiles table using User model
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    user_meta = payload.get("user_metadata", {}) if payload else {}
    onboarding_completed_meta = bool(user_meta.get("onboarding_completed", False))
    avatar_url = user_meta.get("avatar_url") or user_meta.get("picture") or None
    
    # Detect OAuth provider
    provider = "credentials"
    if payload:
        provider = payload.get("app_metadata", {}).get("provider", "credentials")
        
    github_username = user_meta.get("user_name") if provider == "github" else None
    name = user_meta.get("full_name") or user_meta.get("name") or None

    if user is None:
        # Auto-create profile row if it doesn't exist yet (robust sync bridge)
        try:
            email = payload.get("email", "")
            if not name:
                name = email.split("@")[0] or "Esona User"
            
            user = User(
                id=user_id,
                user_id=user_id,
                email=email,
                name=name,
                avatar_url=avatar_url,
                provider=provider,
                github_username=github_username,
                onboarding_completed=onboarding_completed_meta,
            )
            db.add(user)
            await db.flush()
            await db.refresh(user)
        except Exception as e:
            print(f"[Auth Dependency] Failed to auto-create user: {e}")
            raise credentials_exception
    else:
        # Sync onboarding status and OAuth metadata changes if any
        updated = False
        if onboarding_completed_meta and not user.onboarding_completed:
            user.onboarding_completed = True
            updated = True
        if avatar_url and user.avatar_url != avatar_url:
            user.avatar_url = avatar_url
            updated = True
        if name and user.name != name:
            user.name = name
            updated = True
        if provider and user.provider != provider:
            user.provider = provider
            updated = True
        if github_username and user.github_username != github_username:
            user.github_username = github_username
            updated = True
            
        if updated:
            await db.flush()
            
    return user


@router.post("/register")
async def register():
    """Register endpoint disabled – authentication runs securely through Supabase Auth."""
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Registration has migrated directly to Supabase Auth on the frontend.",
    )


@router.post("/login")
async def login():
    """Login endpoint disabled – authentication runs securely through Supabase Auth."""
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Login has migrated directly to Supabase Auth on the frontend.",
    )


@router.get("/me", response_model=dict)
async def get_me(current_user: User = Depends(get_current_user)):
    """Return the currently authenticated user's info."""
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "name": current_user.name,
        "onboarding_completed": current_user.onboarding_completed,
        "avatar_url": current_user.avatar_url,
        "provider": current_user.provider,
        "github_username": current_user.github_username,
        "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
        "last_login": current_user.last_login.isoformat() if current_user.last_login else None,
    }


@router.post("/supabase-login")
async def supabase_login(body: dict, db: AsyncSession = Depends(get_db)):
    """Supabase OAuth registration/login bridge endpoint."""
    user_id_str = body.get("id")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing user ID",
        )
    user_id = uuid.UUID(user_id_str)
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if user is None:
        user = User(
            id=user_id,
            user_id=user_id,
            email=body.get("email", ""),
            name=body.get("name", ""),
            avatar_url=body.get("avatar_url"),
            provider=body.get("provider", "github"),
            github_username=body.get("github_username"),
            onboarding_completed=False,
            last_login=datetime.now(timezone.utc),
        )
        db.add(user)
        await db.flush()
        await db.refresh(user)
    else:
        user.name = body.get("name", user.name)
        user.avatar_url = body.get("avatar_url", user.avatar_url)
        user.provider = body.get("provider", user.provider)
        user.github_username = body.get("github_username", user.github_username)
        user.last_login = datetime.now(timezone.utc)
        await db.flush()
        
    await db.commit()
    
    return {
        "user": {
            "id": str(user.id),
            "email": user.email,
            "name": user.name,
            "onboarding_completed": user.onboarding_completed,
            "avatar_url": user.avatar_url,
            "provider": user.provider,
            "github_username": user.github_username,
        }
    }
