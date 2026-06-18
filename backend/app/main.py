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
    try:
        # Create database tables automatically in dev/production if not present
        await create_tables()
        logger.info("Database tables initialized successfully.")
    except Exception as e:
        logger.critical(f"Database initialization failed: {e}", exc_info=True)
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
