"""
Authentication route – verifies Supabase JWT token and extracts user profile info.
Also provides account deletion with full data cascade.
"""

import uuid
import httpx
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

# ── JWT bearer scheme ────────────────────────────────────────
bearer_scheme = HTTPBearer()


def decode_and_verify_token(token: str) -> dict:
    """Decodes and verifies a JWT token (supporting JWKS verification, Supabase JWT, and local fallback)."""
    # Mask token for logs
    masked_token = f"{token[:8]}...{token[-8:]}" if len(token) > 16 else "***"
    
    # Extract JWT header properties to get alg and kid
    try:
        unverified_header = jwt.get_unverified_header(token)
        alg = unverified_header.get("alg", "HS256")
        kid = unverified_header.get("kid")
    except Exception as header_err:
        logger.warning(f"[AUTH] Failed to parse JWT header: {header_err}")
        alg = "HS256"
        kid = None

    # 1. Try JWKS Verification if token is signed asymmetrically (ES256, RS256)
    if alg in ("ES256", "RS256"):
        try:
            unverified_claims = jwt.get_unverified_claims(token)
            iss = unverified_claims.get("iss")
            if iss and iss.startswith("http"):
                # Avoid duplicating /auth/v1
                if "/auth/v1" in iss:
                    jwks_url = f"{iss.rstrip('/')}/jwks"
                else:
                    jwks_url = f"{iss.rstrip('/')}/auth/v1/jwks"
                    
                logger.info(f"[AUTH] Token algorithm: {alg}. Fetching JWKS from: {jwks_url}...")
                
                if kid:
                    with httpx.Client(timeout=4.0) as client:
                        r = client.get(jwks_url)
                        r.raise_for_status()
                        jwks = r.json()
                    
                    # Find matching key
                    key = None
                    for k in jwks.get("keys", []):
                        if k.get("kid") == kid:
                            key = k
                            break
                    
                    if key:
                        logger.info(f"[AUTH] Found key matching kid '{kid}' in JWKS. Decoding token...")
                        payload = jwt.decode(
                            token,
                            key,
                            algorithms=[alg],
                            options={"verify_aud": False}
                        )
                        logger.info("[AUTH] Token decoded successfully using JWKS.")
                        return payload
                    else:
                        logger.warning(f"[AUTH] Key ID '{kid}' not found in JWKS.")
        except Exception as jwks_err:
            print("JWKS VERIFY FAILED:", jwks_err)
            logger.warning(f"[AUTH] JWKS verification failed: {jwks_err}. Falling back...")

    # 2. Try Supabase JWT Secret Verification (for HS256 setups)
    try:
        jwt_secret = getattr(settings, "SUPABASE_JWT_SECRET", None)
        print("SUPABASE_JWT_SECRET SET:", bool(jwt_secret), "LENGTH:", len(jwt_secret) if jwt_secret else 0)
        if jwt_secret:
            logger.info(f"[AUTH] Attempting to decode token {masked_token} with SUPABASE_JWT_SECRET (alg={alg})...")
            payload = jwt.decode(
                token, settings.SUPABASE_JWT_SECRET, algorithms=[alg], options={"verify_aud": False}
            )
            logger.info("[AUTH] Token successfully decoded with Supabase JWT Secret.")
            return payload
        else:
            logger.warning("[AUTH] SUPABASE_JWT_SECRET not set. Reading unverified claims.")
            payload = jwt.get_unverified_claims(token)
            return payload
    except Exception as supabase_err:
        print("SUPABASE VERIFY FAILED:", supabase_err)
        logger.warning(f"[AUTH] Supabase verification failed: {supabase_err}. Trying local JWT fallback...")
        try:
            # Fallback to local JWT signature
            payload = jwt.decode(
                token, settings.JWT_SECRET, algorithms=[alg]
            )
            logger.info("[AUTH] Token successfully decoded with local JWT secret.")
            return payload
        except (JWTError, ValueError) as local_err:
            print("LOCAL JWT VERIFY FAILED:", local_err)
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
    print("AUTH HEADER:", auth_header)
    print("TOKEN RECEIVED:", token[:20])
    masked_header = f"Bearer {auth_header[7:15]}...{auth_header[-8:]}" if len(auth_header) > 20 else auth_header
    logger.info(f"[AUTH] Incoming request to {request.url.path} with header: '{masked_header}'")

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = decode_and_verify_token(token)
        print("JWT VERIFY SUCCESS")
        user_id_str: str | None = payload.get("sub")
        if user_id_str is None:
            logger.error("[AUTH] Sub claim is missing from JWT payload.")
            raise credentials_exception
        user_id = uuid.UUID(user_id_str)
        logger.info(f"[AUTH] Token verified. Decoded user_id: {user_id}")
    except Exception as e:
        print("JWT VERIFY FAILED:", e)
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


# ── Account Deletion ──────────────────────────────────────────
@router.delete("/account", response_model=dict)
async def delete_account(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Permanently delete the authenticated user's account and ALL associated data.

    Deletion order (respects FK constraints):
      1. emotion_logs
      2. mood_logs
      3. knowledge_graph
      4. memories
      5. chat_messages  (via conversations cascade)
      6. conversations
      7. user_answers (onboarding)
      8. user_question_answers
      9. user_personal_profile
     10. user_personality
     11. profiles (User row)

    After DB wipe → Supabase Admin API deletes the auth account.
    If DB transaction fails → full rollback, nothing is deleted.
    """
    user_id: uuid.UUID = current_user.id
    user_email: str = current_user.email
    user_id_str = str(user_id)

    logger.info(f"[ACCOUNT_DELETION] Initiated for user_id={user_id_str} email={user_email}")

    try:
        # ── Import all models needed ─────────────────────────
        from app.models.emotion_log import EmotionLog
        from app.models.mood_log import MoodLog
        from app.models.knowledge_graph import KnowledgeGraphRelation
        from app.models.memory import Memory
        from app.models.conversation import Conversation, Message
        from app.models.onboarding import UserAnswer
        from app.models.user_personal_profile import UserPersonalProfile

        # Try to import user_personality (may not exist in all environments)
        try:
            from app.models.user_profile import UserProfile
            has_user_profile = True
        except ImportError:
            has_user_profile = False

        # ── 1. Emotion Logs ───────────────────────────────────
        await db.execute(delete(EmotionLog).where(EmotionLog.user_id == user_id))
        logger.info(f"[ACCOUNT_DELETION] emotion_logs deleted for {user_id_str}")

        # ── 2. Mood Logs ──────────────────────────────────────
        await db.execute(delete(MoodLog).where(MoodLog.user_id == user_id))
        logger.info(f"[ACCOUNT_DELETION] mood_logs deleted for {user_id_str}")

        # ── 3. Knowledge Graph ────────────────────────────────
        await db.execute(
            delete(KnowledgeGraphRelation).where(KnowledgeGraphRelation.user_id == user_id)
        )
        logger.info(f"[ACCOUNT_DELETION] knowledge_graph deleted for {user_id_str}")

        # ── 4. Memories ───────────────────────────────────────
        await db.execute(delete(Memory).where(Memory.user_id == user_id))
        logger.info(f"[ACCOUNT_DELETION] memories deleted for {user_id_str}")

        # ── 5. Chat Messages (via conversation cascade) ───────
        # Fetch conversation IDs first, then delete messages
        conv_result = await db.execute(
            select(Conversation.id).where(Conversation.user_id == user_id)
        )
        conv_ids = [row[0] for row in conv_result.fetchall()]
        if conv_ids:
            await db.execute(delete(Message).where(Message.conversation_id.in_(conv_ids)))
            logger.info(f"[ACCOUNT_DELETION] chat_messages deleted for {len(conv_ids)} conversations")

        # ── 6. Conversations ──────────────────────────────────
        await db.execute(delete(Conversation).where(Conversation.user_id == user_id))
        logger.info(f"[ACCOUNT_DELETION] conversations deleted for {user_id_str}")

        # ── 7. Onboarding Answers ─────────────────────────────
        await db.execute(delete(UserAnswer).where(UserAnswer.user_id == user_id))
        logger.info(f"[ACCOUNT_DELETION] user_answers deleted for {user_id_str}")

        # ── 8. User Personal Profile ──────────────────────────
        await db.execute(
            delete(UserPersonalProfile).where(UserPersonalProfile.user_id == user_id)
        )
        logger.info(f"[ACCOUNT_DELETION] user_personal_profile deleted for {user_id_str}")

        # ── 9. User Personality / Profile ─────────────────────
        if has_user_profile:
            await db.execute(delete(UserProfile).where(UserProfile.user_id == user_id))
            logger.info(f"[ACCOUNT_DELETION] user_personality deleted for {user_id_str}")

        # ── 10. User row (profiles table) ────────────────────
        await db.execute(delete(User).where(User.id == user_id))
        logger.info(f"[ACCOUNT_DELETION] profiles row deleted for {user_id_str}")

        # Commit the entire transaction atomically
        await db.commit()
        logger.info(f"[ACCOUNT_DELETION] DB transaction committed successfully for {user_id_str}")

    except Exception as db_err:
        await db.rollback()
        logger.error(
            f"[ACCOUNT_DELETION] DB transaction FAILED and ROLLED BACK for {user_id_str}: {db_err}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Account deletion failed during data removal. No data was deleted. Please try again.",
        )

    # ── Supabase Admin API — Delete Auth Account ──────────────
    supabase_deletion_success = False
    if settings.SUPABASE_URL and settings.SUPABASE_SERVICE_ROLE_KEY:
        try:
            admin_url = f"{settings.SUPABASE_URL.rstrip('/')}/auth/v1/admin/users/{user_id_str}"
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.delete(
                    admin_url,
                    headers={
                        "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
                        "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
                    },
                )
                if resp.status_code in (200, 204):
                    supabase_deletion_success = True
                    logger.info(
                        f"[ACCOUNT_DELETION] Supabase auth account deleted for {user_id_str}"
                    )
                else:
                    logger.warning(
                        f"[ACCOUNT_DELETION] Supabase auth deletion returned {resp.status_code} "
                        f"for {user_id_str}: {resp.text}"
                    )
        except Exception as supa_err:
            logger.warning(
                f"[ACCOUNT_DELETION] Supabase auth deletion failed for {user_id_str}: {supa_err}"
            )
    else:
        logger.warning(
            "[ACCOUNT_DELETION] SUPABASE_SERVICE_ROLE_KEY not set — "
            "auth account NOT deleted from Supabase Auth. Data was wiped from DB."
        )

    logger.info(
        f"[ACCOUNT_DELETION] COMPLETE — user_id={user_id_str} email={user_email} "
        f"supabase_auth_deleted={supabase_deletion_success} "
        f"timestamp={datetime.now(timezone.utc).isoformat()}"
    )

    return {
        "deleted": True,
        "user_id": user_id_str,
        "email": user_email,
        "supabase_auth_deleted": supabase_deletion_success,
    }
