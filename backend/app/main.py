from contextlib import asynccontextmanager
import logging
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

try:
    from app.api.routes import router as api_router
    from app.config import settings
    from app.db.database import get_db, init_db
except ImportError:
    from backend.app.api.routes import router as api_router
    from backend.app.config import settings
    from backend.app.db.database import get_db, init_db


# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("eventmate.backend")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Idempotent database initialization
    logger.info("Initializing database tables...")
    init_db()
    logger.info("Database initialized.")
    settings.log_startup_summary()
    yield


app = FastAPI(
    title="EventMate AI API",
    description="GenAI Celebration & Event Planner Backend",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS Middleware with explicit HTTP methods and allow_credentials=False
cors_kwargs = {
    "allow_origins": settings.allowed_origins_list,
    "allow_credentials": False,
    "allow_methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    "allow_headers": ["*"],
}
if settings.cors_origin_regex:
    cors_kwargs["allow_origin_regex"] = settings.cors_origin_regex

app.add_middleware(CORSMiddleware, **cors_kwargs)


# Exception Handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = []
    for err in exc.errors():
        field = " -> ".join(str(loc) for loc in err.get("loc", []))
        msg = err.get("msg", "Invalid value")
        errors.append({"field": field, "message": msg})
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Validation error in request parameters",
            "errors": errors
        }
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    headers = getattr(exc, "headers", None)
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=headers,
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    return JSONResponse(
        status_code=422,
        content={"detail": str(exc)}
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled server error: %s", exc.__class__.__name__)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred. Please try again later."}
    )


# Root health check endpoint (cheap, unchanged contract)
@app.get("/health", tags=["System"])
async def root_health_check():
    return {
        "status": "ok",
        "ai_configured": settings.is_ai_configured,
        "model": settings.gemini_model if settings.is_ai_configured else "demo"
    }


# Production readiness check (verifies database connectivity)
@app.get("/health/ready", tags=["System"])
def readiness_check(db: Session = Depends(get_db)):
    try:
        db.execute(select(1))
        return {"status": "ok", "database": "ok"}
    except Exception as exc:
        logger.error("Readiness check database failure: %s", type(exc).__name__)
        return JSONResponse(
            status_code=503,
            content={"status": "degraded", "database": "error"}
        )


# Include API Router under /api
app.include_router(api_router, prefix="/api")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host=settings.host, port=settings.port, reload=True)
