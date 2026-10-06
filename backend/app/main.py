import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config.settings import settings

from app.db.base import Base  # noqa: F401
import app.models.user  # noqa: F401
import app.models.task  # noqa: F401
import app.models.goal  # noqa: F401
import app.models.habit  # noqa: F401
import app.models.habit_completion  # noqa: F401
import app.models.planner_event  # noqa: F401
import app.models.note  # noqa: F401
import app.models.transaction  # noqa: F401
import app.models.notification  # noqa: F401
import app.models.user_preferences  # noqa: F401
import app.models.reminder  # noqa: F401
from app.api.v1.router import api_router
from app.services.reminder_scheduler import start_scheduler

logger = logging.getLogger(__name__)

# Without this, `logger.error(...)` in the scheduler and the global exception
# handler has no handler configured and Python's "last resort" fallback writes
# bare messages to stderr with no timestamp or level — which is exactly the
# signal an operator needs when a background tick fails in production.
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
)

app = FastAPI(
    title="AI LifeOS API",
    description="AI-powered personal productivity and finance platform.",
    version="1.0.0",
    # Never serve the interactive /docs and /redoc UIs in production: they
    # advertise the full route surface to anyone who loads the page.
    docs_url=None if not settings.DEBUG else "/docs",
    redoc_url=None if not settings.DEBUG else "/redoc",
    openapi_url=None if not settings.DEBUG else "/openapi.json",
)

# The reminder scheduler runs as an in-process asyncio task bound to the app
# lifespan: it starts with the backend and shuts down cleanly with it.
start_scheduler(app)

# In production the allow-list comes from CORS_ORIGINS. The localhost origins
# are kept only as a development convenience so `npm run dev` works with no
# configuration; a production deployment is expected to set CORS_ORIGINS and
# leave DEBUG=false, which drops them entirely.
LOCAL_DEV_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
]

configured_origins = settings.allowed_origins()

if configured_origins:
    allow_origins = configured_origins
else:
    if not settings.DEBUG:
        logger.warning(
            "CORS_ORIGINS is not set. Every cross-origin browser request will "
            "be rejected. Set CORS_ORIGINS to the frontend's public origin "
            "before deploying."
        )
    allow_origins = LOCAL_DEV_ORIGINS

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """
    Baseline response headers.

    `X-Content-Type-Options` stops a browser from re-interpreting a JSON error
    body as HTML, and `X-Frame-Options`/`Referrer-Policy` close the easy
    clickjacking and referrer-leak paths. None of these change API behaviour,
    and no CSP is set here because this service only ever returns JSON.
    """

    response = await call_next(request)

    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")

    return response


app.include_router(api_router)


@app.exception_handler(Exception)
async def app_exception_handler(request: Request, exc: Exception):
    """
    Global exception handler that prevents stack traces / internal detail from
    leaking to clients. The full traceback is always logged server-side; the
    response body is a short, generic message in both DEBUG and production, so
    toggling DEBUG can never start exposing internals over HTTP.
    """

    logger.error(
        "Unhandled exception on %s %s",
        request.method,
        request.url.path,
        exc_info=exc,
    )

    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred."},
    )


@app.get("/", tags=["Root"])
def root():
    """
    Service banner.

    Deliberately does not report "operational". A hardcoded status string on a
    root endpoint is exactly the kind of fake-ready signal that lets a broken
    deployment look healthy; `/api/v1/health` is the endpoint that actually
    checks anything.
    """

    return {
        "message": "Welcome to AI LifeOS API",
        "version": "1.0.0",
        "docs": "/api/v1/health",
    }