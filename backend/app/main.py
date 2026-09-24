"""FastAPI app: the API, the web app and the Telegram webhook in one service."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .bot.telegram import router as telegram_router
from .config import CATEGORY_LABELS, LANGUAGES, settings
from .db import store
from .engine import classifier, llm
from .pipeline import analyze
from .schemas import AnalyzeResult, FeedbackIn, ReportIn, StatsOut

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
WEB_DIR = Path(__file__).resolve().parents[1] / "web"


@asynccontextmanager
async def lifespan(app: FastAPI):
    store.init_db()
    logging.getLogger("safesaathi").info(
        "started | gemini=%s | classifier=%s | telegram=%s",
        llm.available(), classifier.available(), settings.has_telegram)
    yield


app = FastAPI(
    title="SafeSaathi API",
    version="1.0.0",
    description="Forward any suspicious message. Get a verdict, the reasons, and what to do.",
    lifespan=lifespan,
)

origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()] or ["*"]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=False,
                   allow_methods=["*"], allow_headers=["*"])


@app.get("/health", tags=["meta"])
def health() -> dict[str, object]:
    return {"ok": True, "gemini": llm.available(), "classifier": classifier.available(),
            "telegram": settings.has_telegram}


@app.get("/api/meta", tags=["meta"])
def meta() -> dict[str, object]:
    return {"languages": LANGUAGES, "categories": CATEGORY_LABELS,
            "engine": "gemini" if llm.available() else "rules+classifier"}


@app.post("/api/analyze", response_model=AnalyzeResult, tags=["check"])
async def analyze_route(
    kind: str = Form("text"),
    content: str = Form(""),
    lang: str = Form("en"),
    source: str = Form("web"),
    user_ref: str = Form(""),
    want_audio: bool = Form(False),
    file: UploadFile | None = File(None),
) -> AnalyzeResult:
    data = await file.read() if file is not None else None
    mime = file.content_type if file is not None else None
    result = await analyze(kind=kind, content=content, data=data, mime=mime, lang=lang,
                           source=source, user_ref=user_ref, want_audio=want_audio)
    return AnalyzeResult(**result)


@app.get("/api/stats", response_model=StatsOut, tags=["dashboard"])
def stats_route() -> StatsOut:
    return StatsOut(**store.stats())


@app.post("/api/feedback", tags=["check"])
def feedback_route(payload: FeedbackIn) -> dict[str, bool]:
    store.add_feedback(payload.fingerprint, payload.says_scam, payload.source)
    return {"ok": True}


@app.post("/api/report", tags=["check"])
def report_route(payload: ReportIn) -> dict[str, object]:
    count = store.add_report(payload.kind, payload.value, payload.source)
    return {"ok": True, "reports": count}


app.include_router(telegram_router)

if WEB_DIR.exists():
    app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")

    @app.get("/", include_in_schema=False)
    def home() -> FileResponse:
        return FileResponse(WEB_DIR / "index.html")

    @app.get("/dashboard", include_in_schema=False)
    def dashboard() -> FileResponse:
        return FileResponse(WEB_DIR / "dashboard.html")
