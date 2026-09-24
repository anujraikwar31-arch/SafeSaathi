"""One check, end to end: read it, test it, judge it, explain it, remember it."""
from __future__ import annotations

import asyncio
import hashlib
import logging
import time
from typing import Any

from .config import CATEGORIES, LANGUAGES, settings
from .db import fingerprint as fp_mod
from .db import store
from .engine import classifier, fallback, links, llm, ocr, rules, tts
from .engine import upi as upi_mod

log = logging.getLogger("safesaathi.pipeline")

SCAM_AT = 70
SUSPICIOUS_AT = 40


def verdict_for(risk: int) -> str:
    if risk >= SCAM_AT:
        return "SCAM"
    if risk >= SUSPICIOUS_AT:
        return "SUSPICIOUS"
    return "SAFE"


def _hash_user(user_ref: str) -> str:
    if not user_ref:
        return ""
    return hashlib.sha256(f"safesaathi:{user_ref}".encode()).hexdigest()[:16]


async def fast_checks(text: str) -> dict[str, Any]:
    """Rules, links, UPI and the classifier. None of them may raise."""
    async def link_task() -> list[dict[str, Any]]:
        try:
            return await asyncio.wait_for(links.check_all(text), timeout=8)
        except Exception:
            return []

    link_signals, rule_hits, upi_info, score = await asyncio.gather(
        link_task(),
        asyncio.to_thread(rules.check, text),
        asyncio.to_thread(upi_mod.check, text),
        asyncio.to_thread(classifier.score, text),
        return_exceptions=False,
    )
    return {"rules": rule_hits, "links": link_signals, "upi": upi_info, "classifier": score}


def findings_for_prompt(findings: dict[str, Any]) -> dict[str, Any]:
    """The short version of the evidence that goes to Gemini."""
    return {
        "red_flag_rules": findings["rules"],
        "classifier_scam_probability": round(findings["classifier"], 3)
        if findings["classifier"] is not None else None,
        "links": [
            {k: v for k, v in link.items() if k in
             ("domain", "age_days", "lookalike", "safe_browsing", "shortened", "risky_tld")}
            for link in findings["links"]
        ],
        "upi_ids_found": findings["upi"]["upi_ids"],
        "times_reported_by_users": findings["upi"]["reported_before"],
    }


def combine(gemini: dict[str, Any] | None, findings: dict[str, Any]) -> int:
    hits = findings["rules"]
    flags = min(len(hits), 3)
    probability = findings["classifier"]

    if gemini is not None:
        risk = 0.6 * gemini["risk"] + 10 * flags
        risk += 25 * probability if probability is not None else 0.15 * gemini["risk"]
    elif probability is not None:
        risk = 70 * probability + 14 * flags
    else:
        risk = 22 * flags

    worst_link = links.worst(findings["links"])
    if worst_link:
        if worst_link.get("safe_browsing"):
            risk = max(risk, 95)
        if worst_link.get("lookalike"):
            risk = max(risk, 75)
        if worst_link.get("age_days") is not None and worst_link["age_days"] < 30:
            risk = max(risk, 65)
        if worst_link.get("shortened") or worst_link.get("risky_tld"):
            risk = max(risk, 45)

    if rules.hard_hits(hits):
        risk = max(risk, 80)
    if findings["upi"]["reported_before"]:
        risk = max(risk, 70)

    return int(max(0, min(100, round(risk))))


def _unreadable(lang: str, started: float) -> dict[str, Any]:
    message = fallback.UNREADABLE.get(lang, fallback.UNREADABLE["en"])
    return {
        "verdict": "SUSPICIOUS", "risk": 50, "category": "other_scam",
        "reasons": [message], "advice": fallback.ADVICE["SUSPICIOUS"].get(lang, fallback.ADVICE["SUSPICIOUS"]["en"]),
        "extracted_text": "", "signals": {"engine": "none"}, "seen_count": 1, "cached": False,
        "fingerprint": "", "audio_b64": None, "lang": lang,
        "latency_ms": int((time.time() - started) * 1000),
    }


async def analyze(kind: str = "text", content: str = "", data: bytes | None = None,
                  mime: str | None = None, lang: str = "en", source: str = "web",
                  user_ref: str = "", want_audio: bool = False) -> dict[str, Any]:
    started = time.time()
    lang = lang if lang in LANGUAGES else settings.default_lang
    text = (content or "").strip()
    gemini: dict[str, Any] | None = None
    engine_used = "fallback"

    # 1. Screenshots and voice notes: get the words out first.
    if kind in ("image", "audio") and data:
        if llm.available():
            gemini = await asyncio.to_thread(llm.judge, text, {}, lang, data, mime)
            if gemini:
                engine_used = "gemini"
                text = (gemini.get("extracted_text") or text).strip()
        if not text and kind == "image":
            text = ocr.read_image(data)
        if not text:
            return _unreadable(lang, started)

    if not text:
        return _unreadable(lang, started)

    finger = fp_mod.make(text)
    is_test = source == "test"

    # 2. Have we seen this exact template before?
    if not is_test:
        cached = store.get_template(finger, lang)
        if cached:
            store.bump_template(finger, lang)
            seen = store.seen_total(finger)
            store.log_check(source=source, kind=kind, lang=lang, fingerprint=finger,
                            verdict=cached["verdict"], risk=cached["risk"],
                            category=cached["category"], cached=True,
                            latency_ms=int((time.time() - started) * 1000),
                            user_ref=_hash_user(user_ref))
            audio = None
            if want_audio:
                audio = tts.speak(tts.spoken_script(cached["verdict"], cached["reasons"],
                                                    cached["advice"], lang), lang)
            return {
                "verdict": cached["verdict"], "risk": cached["risk"],
                "category": cached["category"], "reasons": cached["reasons"],
                "advice": cached["advice"], "extracted_text": text,
                "signals": {"engine": "cache"}, "seen_count": seen, "cached": True,
                "fingerprint": finger, "audio_b64": audio, "lang": lang,
                "latency_ms": int((time.time() - started) * 1000),
            }

    # 3. Fast checks, then Gemini with the evidence in hand.
    findings = await fast_checks(text)
    if gemini is None and llm.available():
        try:
            gemini = await asyncio.wait_for(
                asyncio.to_thread(llm.judge, text, findings_for_prompt(findings), lang),
                timeout=20)
        except Exception as exc:
            log.warning("gemini call failed: %s", exc)
            gemini = None
        if gemini:
            engine_used = "gemini"

    risk = combine(gemini, findings)
    verdict = verdict_for(risk)

    if gemini and gemini.get("reasons"):
        reasons = gemini["reasons"][:3]
        advice = gemini.get("advice") or fallback.ADVICE[verdict].get(lang, fallback.ADVICE[verdict]["en"])
        category = gemini.get("category") if gemini.get("category") in CATEGORIES else None
        if not category:
            category = fallback.build(findings["rules"], findings["links"], findings["upi"],
                                      findings["classifier"], verdict, lang)["category"]
    else:
        built = fallback.build(findings["rules"], findings["links"], findings["upi"],
                               findings["classifier"], verdict, lang)
        reasons, advice, category = built["reasons"], built["advice"], built["category"]

    if verdict == "SAFE":
        category = "not_scam"

    # 4. Remember the template so the next copy is instant.
    if not is_test:
        store.save_template(finger, lang, verdict, risk, category,
                            fp_mod.snippet(text), reasons, advice)
    seen = store.seen_total(finger) if not is_test else 1
    store.log_check(source=source, kind=kind, lang=lang, fingerprint=finger, verdict=verdict,
                    risk=risk, category=category, cached=False,
                    latency_ms=int((time.time() - started) * 1000), user_ref=_hash_user(user_ref))

    audio = None
    if want_audio:
        audio = tts.speak(tts.spoken_script(verdict, reasons, advice, lang), lang)

    return {
        "verdict": verdict,
        "risk": risk,
        "category": category,
        "reasons": reasons,
        "advice": advice,
        "extracted_text": text,
        "signals": {
            "rules": findings["rules"],
            "classifier": round(findings["classifier"], 3) if findings["classifier"] is not None else None,
            "gemini_risk": gemini["risk"] if gemini else None,
            "engine": engine_used,
            "links": findings["links"],
            "upi_ids": findings["upi"]["upi_ids"],
            "phones": findings["upi"]["phones"],
            "reported_before": findings["upi"]["reported_before"],
        },
        "seen_count": seen,
        "cached": False,
        "fingerprint": finger,
        "audio_b64": audio,
        "lang": lang,
        "latency_ms": int((time.time() - started) * 1000),
    }
