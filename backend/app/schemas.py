"""The API contract. Every client (web app, Telegram bot, tests) uses these shapes."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

Verdict = Literal["SAFE", "SUSPICIOUS", "SCAM"]
Kind = Literal["text", "image", "audio", "link", "upi"]


class LinkSignal(BaseModel):
    url: str
    domain: str = ""
    shortened: bool = False
    expanded_to: str | None = None
    age_days: int | None = None
    lookalike: str | None = None
    risky_tld: bool = False
    safe_browsing: bool = False


class Signals(BaseModel):
    rules: list[str] = Field(default_factory=list)
    classifier: float | None = None
    gemini_risk: int | None = None
    engine: str = "fallback"  # "gemini" or "fallback"
    links: list[LinkSignal] = Field(default_factory=list)
    upi_ids: list[str] = Field(default_factory=list)
    phones: list[str] = Field(default_factory=list)
    reported_before: int = 0


class AnalyzeResult(BaseModel):
    verdict: Verdict
    risk: int
    category: str
    reasons: list[str]
    advice: str
    extracted_text: str = ""
    signals: Signals = Field(default_factory=Signals)
    seen_count: int = 1
    cached: bool = False
    fingerprint: str = ""
    audio_b64: str | None = None
    lang: str = "en"
    latency_ms: int = 0


class FeedbackIn(BaseModel):
    fingerprint: str
    says_scam: bool
    source: str = "web"


class ReportIn(BaseModel):
    kind: Literal["upi", "phone", "url"]
    value: str
    source: str = "web"


class StatsOut(BaseModel):
    total_checks: int
    checks_today: int
    by_verdict: dict[str, int]
    by_category: list[dict[str, Any]]
    daily: list[dict[str, Any]]
    trending: list[dict[str, Any]]
    languages_used: int
    scam_share: float
