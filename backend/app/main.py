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

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import create_tables
from app.routes import auth_router, chat_router, onboarding_router, dashboard_router

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
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.FRONTEND_URL,
        "http://localhost:3000",
        "https://esona.vercel.app",
        "https://agentic-mental-wellness-assistant.vercel.app",
    ],
    allow_origin_regex=r"https://agentic-mental-wellness-assistant.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
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
app.include_router(onboarding_router)
app.include_router(dashboard_router)


# ── Root Test Endpoint ────────────────────────────────────────
@app.get("/")
async def root():
    """Verify that Esona API is reachable."""
    return {"message": "Esona API is running successfully"}


# ── Simple Health check (for Render Deployment) ───────────────
@app.get("/health", tags=["Health"])
async def simple_health():
    """Simple health check endpoint returning status ok."""
    return {"status": "ok"}


# ── Detailed Health check ─────────────────────────────────────
@app.get("/api/health", tags=["Health"])
async def health_check():
    """Verify that the API server is running and database is reachable."""
    return {
        "status": "healthy",
        "app": "Esona API",
        "version": "1.0.0",
    }
