"""Data layer. SQLite by default, Postgres (Supabase) when DATABASE_URL points at one."""
from __future__ import annotations

import datetime as dt
import json
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    create_engine,
    delete,
    func,
    insert,
    select,
    update,
)

from ..config import settings

_url = settings.database_url
if _url.startswith("postgres://"):  # Supabase hands out this older prefix
    _url = _url.replace("postgres://", "postgresql+psycopg://", 1)
elif _url.startswith("postgresql://"):
    _url = _url.replace("postgresql://", "postgresql+psycopg://", 1)

engine = create_engine(_url, future=True, pool_pre_ping=True)
meta = MetaData()


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)


checks = Table(
    "checks", meta,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("created_at", DateTime, default=_now),
    Column("source", String(16)),
    Column("kind", String(16)),
    Column("lang", String(8)),
    Column("fingerprint", String(32)),
    Column("verdict", String(16)),
    Column("risk", Integer),
    Column("category", String(40)),
    Column("cached", Boolean, default=False),
    Column("latency_ms", Integer),
    Column("user_ref", String(64)),
)

templates = Table(
    "templates", meta,
    Column("fingerprint", String(32), primary_key=True),
    Column("lang", String(8), primary_key=True),
    Column("first_seen", DateTime, default=_now),
    Column("last_seen", DateTime, default=_now),
    Column("seen_count", Integer, default=1),
    Column("verdict", String(16)),
    Column("risk", Integer),
    Column("category", String(40)),
    Column("snippet", Text),
    Column("reasons", Text),
    Column("advice", Text),
)

reports = Table(
    "reports", meta,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("created_at", DateTime, default=_now),
    Column("kind", String(16)),
    Column("value", String(160)),
    Column("source", String(16)),
)

users = Table(
    "users", meta,
    Column("chat_id", BigInteger, primary_key=True),
    Column("lang", String(8), default="en"),
    Column("guardian_chat_id", BigInteger),
    Column("link_code", String(8)),
    Column("link_code_expires", DateTime),
    Column("created_at", DateTime, default=_now),
)

feedback = Table(
    "feedback", meta,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("created_at", DateTime, default=_now),
    Column("fingerprint", String(32)),
    Column("says_scam", Boolean),
    Column("source", String(16)),
)


def init_db() -> None:
    meta.create_all(engine)


# ---------------------------------------------------------------- templates


def get_template(fingerprint: str, lang: str) -> dict[str, Any] | None:
    with engine.connect() as cx:
        row = cx.execute(
            select(templates).where(
                templates.c.fingerprint == fingerprint, templates.c.lang == lang
            )
        ).mappings().first()
    if not row:
        return None
    out = dict(row)
    out["reasons"] = json.loads(out["reasons"] or "[]")
    return out


def seen_total(fingerprint: str) -> int:
    with engine.connect() as cx:
        total = cx.execute(
            select(func.coalesce(func.sum(templates.c.seen_count), 0)).where(
                templates.c.fingerprint == fingerprint
            )
        ).scalar_one()
    return int(total or 0)


def save_template(fingerprint: str, lang: str, verdict: str, risk: int, category: str,
                  snippet: str, reasons: list[str], advice: str) -> None:
    payload = dict(verdict=verdict, risk=risk, category=category, snippet=snippet,
                   reasons=json.dumps(reasons, ensure_ascii=False), advice=advice,
                   last_seen=_now())
    with engine.begin() as cx:
        exists = cx.execute(
            select(templates.c.fingerprint).where(
                templates.c.fingerprint == fingerprint, templates.c.lang == lang
            )
        ).first()
        if exists:
            cx.execute(
                update(templates)
                .where(templates.c.fingerprint == fingerprint, templates.c.lang == lang)
                .values(seen_count=templates.c.seen_count + 1, **payload)
            )
        else:
            cx.execute(insert(templates).values(
                fingerprint=fingerprint, lang=lang, first_seen=_now(), seen_count=1, **payload
            ))


def bump_template(fingerprint: str, lang: str) -> None:
    with engine.begin() as cx:
        cx.execute(
            update(templates)
            .where(templates.c.fingerprint == fingerprint, templates.c.lang == lang)
            .values(seen_count=templates.c.seen_count + 1, last_seen=_now())
        )


# ------------------------------------------------------------------- checks


def log_check(**values: Any) -> None:
    values.setdefault("created_at", _now())
    with engine.begin() as cx:
        cx.execute(insert(checks).values(**values))


# ------------------------------------------------------- reports / feedback


def add_report(kind: str, value: str, source: str = "web") -> int:
    with engine.begin() as cx:
        cx.execute(insert(reports).values(kind=kind, value=value.lower().strip(),
                                          source=source, created_at=_now()))
    return count_reports(kind, value)


def count_reports(kind: str, value: str) -> int:
    with engine.connect() as cx:
        return int(cx.execute(
            select(func.count()).select_from(reports).where(
                reports.c.kind == kind, reports.c.value == value.lower().strip()
            )
        ).scalar_one())


def add_feedback(fingerprint: str, says_scam: bool, source: str = "web") -> None:
    with engine.begin() as cx:
        cx.execute(insert(feedback).values(fingerprint=fingerprint, says_scam=says_scam,
                                           source=source, created_at=_now()))


# -------------------------------------------------------------------- users


def get_user(chat_id: int) -> dict[str, Any] | None:
    with engine.connect() as cx:
        row = cx.execute(select(users).where(users.c.chat_id == chat_id)).mappings().first()
    return dict(row) if row else None


def ensure_user(chat_id: int, lang: str | None = None) -> dict[str, Any]:
    user = get_user(chat_id)
    if user:
        return user
    with engine.begin() as cx:
        cx.execute(insert(users).values(chat_id=chat_id, lang=lang or settings.default_lang,
                                        created_at=_now()))
    return get_user(chat_id) or {"chat_id": chat_id, "lang": lang or settings.default_lang}


def set_user_lang(chat_id: int, lang: str) -> None:
    ensure_user(chat_id)
    with engine.begin() as cx:
        cx.execute(update(users).where(users.c.chat_id == chat_id).values(lang=lang))


def set_link_code(chat_id: int, code: str, minutes: int = 30) -> None:
    ensure_user(chat_id)
    expires = _now() + dt.timedelta(minutes=minutes)
    with engine.begin() as cx:
        cx.execute(update(users).where(users.c.chat_id == chat_id)
                   .values(link_code=code, link_code_expires=expires))


def find_by_link_code(code: str) -> dict[str, Any] | None:
    with engine.connect() as cx:
        row = cx.execute(select(users).where(users.c.link_code == code)).mappings().first()
    if not row:
        return None
    row = dict(row)
    if row.get("link_code_expires") and row["link_code_expires"] < _now():
        return None
    return row


def link_guardian(parent_chat_id: int, guardian_chat_id: int) -> None:
    with engine.begin() as cx:
        cx.execute(update(users).where(users.c.chat_id == parent_chat_id)
                   .values(guardian_chat_id=guardian_chat_id, link_code=None,
                           link_code_expires=None))


def unlink_guardian(chat_id: int) -> None:
    with engine.begin() as cx:
        cx.execute(update(users).where(users.c.chat_id == chat_id)
                   .values(guardian_chat_id=None, link_code=None, link_code_expires=None))


# --------------------------------------------------------------------- stats


def stats() -> dict[str, Any]:
    today = _now().date()
    week_ago = _now() - dt.timedelta(days=6)
    with engine.connect() as cx:
        rows = cx.execute(
            select(checks.c.created_at, checks.c.verdict, checks.c.category, checks.c.lang)
            .where(checks.c.source != "test")
        ).all()
        trend_rows = cx.execute(
            select(templates.c.snippet, templates.c.category, templates.c.verdict,
                   templates.c.seen_count, templates.c.last_seen)
            .where(templates.c.verdict != "SAFE")
            .order_by(templates.c.seen_count.desc(), templates.c.last_seen.desc())
            .limit(10)
        ).mappings().all()

    by_verdict: dict[str, int] = {"SAFE": 0, "SUSPICIOUS": 0, "SCAM": 0}
    by_category: dict[str, int] = {}
    daily: dict[str, int] = {}
    languages: set[str] = set()
    checks_today = 0

    for created_at, verdict, category, lang in rows:
        by_verdict[verdict] = by_verdict.get(verdict, 0) + 1
        if verdict != "SAFE" and category:
            by_category[category] = by_category.get(category, 0) + 1
        if lang:
            languages.add(lang)
        if created_at:
            if created_at.date() == today:
                checks_today += 1
            if created_at >= week_ago:
                key = created_at.date().isoformat()
                daily[key] = daily.get(key, 0) + 1

    total = len(rows)
    flagged = by_verdict.get("SCAM", 0) + by_verdict.get("SUSPICIOUS", 0)
    days = [(week_ago + dt.timedelta(days=i)).date().isoformat() for i in range(7)]

    return {
        "total_checks": total,
        "checks_today": checks_today,
        "by_verdict": by_verdict,
        "by_category": [
            {"category": k, "count": v}
            for k, v in sorted(by_category.items(), key=lambda kv: -kv[1])
        ],
        "daily": [{"date": d, "checks": daily.get(d, 0)} for d in days],
        "trending": [
            {
                "snippet": r["snippet"],
                "category": r["category"],
                "verdict": r["verdict"],
                "count": r["seen_count"],
                "last_seen": r["last_seen"].isoformat() if r["last_seen"] else None,
            }
            for r in trend_rows
        ],
        "languages_used": len(languages),
        "scam_share": round(100 * flagged / total, 1) if total else 0.0,
    }
