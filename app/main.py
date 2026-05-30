from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.db import init_db, list_companies, save_company
from app.enrichment import enrich_company


BASE_DIR = Path(__file__).resolve().parent.parent


class EnrichRequest(BaseModel):
    url: str = Field(..., min_length=1)
    website_name: str = ""


app = FastAPI(title="AI Company Enrichment")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/", response_class=HTMLResponse)
def home() -> str:
    return (BASE_DIR / "static" / "index.html").read_text(encoding="utf-8")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/enrich")
def enrich(payload: EnrichRequest) -> dict:
    profile = enrich_company(payload.url, payload.website_name)
    save_company(profile)
    return profile


@app.get("/results")
def results() -> list[dict]:
    return list_companies()
