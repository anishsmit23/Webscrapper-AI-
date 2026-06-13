"""FastAPI backend for the AI Company Enrichment system.

Repairs applied:
- #2  Rate limiting via slowapi (5 req/min per IP)
- #3  Async endpoint with asyncio.to_thread for blocking I/O
- #8  URL validation in request model
- #14 Modern lifespan handler (replaces deprecated on_event)
- #15 Structured logging
- #16 CORS kept permissive for demo (note: tighten for production)
- #18 Pydantic response model for /enrich
"""


import asyncio
import logging
import re
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlparse

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.db import init_db, list_companies, save_company
from app.enrichment import enrich_company

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class EnrichRequest(BaseModel):
    url: str = Field(..., min_length=1)
    website_name: str = ""

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        v = v.strip()
        if not re.match(r"^https?://", v, re.I):
            v = "https://" + v
        parsed = urlparse(v)
        if not parsed.netloc or "." not in parsed.netloc:
            raise ValueError(
                "Please provide a valid website URL (e.g. https://example.com)"
            )
        return v


class CompanyProfile(BaseModel):
    """Canonical output schema — every /enrich response matches this."""

    website_name: str = ""
    company_name: str = ""
    address: str = ""
    mobile_number: str = ""
    mail: list[str] = Field(default_factory=list)
    core_service: str = ""
    target_customer: str = ""
    probable_pain_point: str = ""
    outreach_opener: str = ""



@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up — initializing database")
    init_db()
    yield
    logger.info("Shutting down")

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="AI Company Enrichment", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
def home() -> str:
    return (BASE_DIR / "static" / "index.html").read_text(encoding="utf-8")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/enrich", response_model=CompanyProfile)
@limiter.limit("5/minute")
async def enrich(request: Request, payload: EnrichRequest) -> CompanyProfile:
    logger.info("Enrichment requested for URL: %s", payload.url)
    try:
        profile = await asyncio.to_thread(
            enrich_company, payload.url, payload.website_name
        )
        save_company(profile)
        logger.info("Enrichment complete for URL: %s", payload.url)
        return CompanyProfile(**profile)
    except Exception:
        logger.exception("Enrichment failed for URL: %s", payload.url)
        return CompanyProfile(
            website_name=payload.website_name or payload.url,
            company_name=payload.website_name or payload.url,
        )


@app.get("/results")
def results(limit: int = 50, offset: int = 0) -> list[dict]:
    return list_companies(limit=limit, offset=offset)
