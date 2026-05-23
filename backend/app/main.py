"""
FastAPI application entry point.
Set up CORS, routers, exception handlers, and database connection.
"""

from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import create_tables
from app.routers import auth, chat, onboarding, dashboard

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
    description="Backend API for Esona - your supporting buddie",
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS Middleware ──────────────────────────────────────────
# Allow connections from the Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL, "http://localhost:3000"],
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


# ── Include Routers ───────────────────────────────────────────
app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(onboarding.router)
app.include_router(dashboard.router)


# ── Health check ──────────────────────────────────────────────
@app.get("/api/health", tags=["Health"])
async def health_check():
    """Verify that the API server is running and database is reachable."""
    return {
        "status": "healthy",
        "app": "Esona API",
        "version": "1.0.0",
    }
