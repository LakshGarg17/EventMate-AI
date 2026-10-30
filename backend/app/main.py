from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

try:
    from app.api.routes import router as api_router
    from app.config import settings
    from app.db.database import init_db
except ImportError:
    from backend.app.api.routes import router as api_router
    from backend.app.config import settings
    from backend.app.db.database import init_db


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("eventmate.backend")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Idempotent database initialization
    logger.info("Initializing database tables...")
    init_db()
    logger.info("Database initialized.")
    yield


app = FastAPI(
    title="EventMate AI API",
    description="GenAI Celebration & Event Planner Backend",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS Middleware with explicit PUT and DELETE support
origins = settings.allowed_origins_list
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD"],
    allow_headers=["*"],
)


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
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    return JSONResponse(
        status_code=422,
        content={"detail": str(exc)}
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled server error: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred. Please try again later."}
    )


# Root health check endpoint
@app.get("/health", tags=["System"])
async def root_health_check():
    return {
        "status": "ok",
        "ai_configured": settings.is_ai_configured,
        "model": settings.gemini_model if settings.is_ai_configured else "demo"
    }


# Include API Router under /api
app.include_router(api_router, prefix="/api")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host=settings.host, port=settings.port, reload=True)
