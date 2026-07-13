"""
FastAPI application entry point.
Sets up CORS, routes, exception handlers, and database connection.
Contains health check endpoints and test routes.

Folder purpose explanations:
- app/routes: Contains API routers defining REST/SSE endpoints (Auth, Chat, Dashboard, Onboarding).
- app/services: Business logic layers (e.g. profiling, mood tracking).
- app/models: SQLAlchemy database model classes representing schema structure.
- app/schemas: Pydantic request/response validation schemas.
- app/agents: LangGraph multi-agent cognitive architecture.
- app/utils: General utility helper functions.
"""

from contextlib import asynccontextmanager
import logging
from sqlalchemy import text

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import create_tables, engine
from app.routes import auth_router, chat_router, conversations_router, onboarding_router, dashboard_router, insights_router
from app.routes.dashboard import mood_router

# ── Logging ───────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# ── Lifespan event handler ───────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle event handler for database and other service startups."""
    logger.info("Starting up Esona API...")
    
    # 1. Production database guard
    import os
    is_render = os.environ.get("RENDER") == "true" or os.environ.get("ENVIRONMENT") == "production"
    is_sqlite = not settings.is_postgres or "sqlite" in settings.DATABASE_URL or "esona.db" in settings.DATABASE_URL
    
    if is_render and is_sqlite:
        msg = "[DB CRITICAL] Ephemeral SQLite database configured in production/Render environment! Startup aborted to prevent data loss."
        logger.critical(msg)
        raise RuntimeError(msg)

    # 2. Log database configuration details safely
    if settings.is_postgres:
        logger.info("[DB] Database dialect: PostgreSQL")
        logger.info("[DB] Driver: asyncpg")
        logger.info("[DB] Production persistence: external PostgreSQL")
        
        # Mask password and print DB URL for troubleshooting
        from urllib.parse import urlparse
        try:
            parsed = urlparse(settings.DATABASE_URL)
            password_len = len(parsed.password) if parsed.password else 0
            if password_len > 2:
                masked_password = parsed.password[0] + "*" * (password_len - 2) + parsed.password[-1]
            else:
                masked_password = "*" * password_len
            masked_url = f"{parsed.scheme}://{parsed.username}:{masked_password}@{parsed.hostname}:{parsed.port}{parsed.path}"
            logger.info(f"[DB] Connection URL: {masked_url}")
        except Exception as e:
            logger.info(f"[DB] Connection URL could not be parsed: {e}")
    else:
        logger.info("[DB] Database dialect: SQLite")
        logger.info("[DB] Local database path configured")

    # 3. Connection verification (SELECT 1)
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("[DB] Database connection verified")
    except Exception as e:
        logger.critical(f"[DB] Database connection verification failed: {e}")
        # If in production/Render environment, we MUST abort startup
        if is_render or settings.is_postgres:
            logger.critical("[DB] Critical connection failure in production environment. Aborting startup.")
            raise RuntimeError(f"Database connection verification failed: {e}") from e

    try:
        # Create database tables automatically in dev/production if not present
        await create_tables()
        logger.info("Database tables initialized successfully.")
    except Exception as e:
        logger.critical(f"Database initialization failed: {e}", exc_info=True)
        if is_render or settings.is_postgres:
            raise RuntimeError(f"Database table initialization failed: {e}") from e
    yield
    logger.info("Shutting down Esona API...")


# ── App setup ─────────────────────────────────────────────────
app = FastAPI(
    title="Esona API",
    description="Backend API for Esona - your supporting buddy",
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS Middleware (Vercel Production & Local Support) ───────
# Allow connections from Next.js local dev environment and Vercel production/preview deploys
frontend_origins = [
    "https://agentic-mental-wellness-assistant.vercel.app",
    "https://esona.vercel.app",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

if settings.FRONTEND_URL:
    url = settings.FRONTEND_URL.rstrip("/")
    if url not in frontend_origins:
        frontend_origins.append(url)

# Eliminate duplicates in case settings.FRONTEND_URL matches one of the hardcoded URLs
allowed_origins = list(set(frontend_origins))

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=r"https://agentic-mental-wellness-assistant(-[a-z0-9-]+)?\.vercel\.app",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)



# ── Global Exception Handler ───────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception in request {request.url}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred. Please try again later."},
    )


# ── Include Routes ───────────────────────────────────────────
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(conversations_router)
app.include_router(onboarding_router)
app.include_router(dashboard_router)
app.include_router(insights_router)
app.include_router(mood_router)


# ── Root Test Endpoint ────────────────────────────────────────
@app.get("/")
async def root():
    """Verify that Esona API is reachable."""
    return {"message": "Esona API is running successfully"}


# ── Simple Health check (for Render Deployment) ───────────────
@app.get("/health", tags=["Health"])
async def simple_health():
    """Simple health check endpoint returning status ok and pre-warming DB connection."""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        logger.warning(f"Database pre-warm failed: {e}")
        db_status = "error"
    return {"status": "ok", "database": db_status}


# ── Detailed Health check ─────────────────────────────────────
@app.get("/api/health", tags=["Health"])
async def health_check():
    """Verify that the API server is running and database is reachable."""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception as e:
        logger.error(f"Detailed health check database connection failed: {e}")
        db_status = "unhealthy"
    return {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "app": "Esona API",
        "version": "1.0.0",
        "database": db_status,
    }
