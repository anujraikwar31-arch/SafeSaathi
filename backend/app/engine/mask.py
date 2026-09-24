"""Remove personal details before anything leaves our server.

Gemini's free tier may use prompts to improve Google products, so phone numbers,
account numbers and email addresses are replaced before the call. Small amounts
such as Rs 499 are kept, because they matter to the verdict.
"""
from __future__ import annotations

import re

_EMAIL = re.compile(r"\b[\w.\-+]+@[\w\-]+\.[a-z]{2,}\b", re.I)
_PHONE = re.compile(r"(?:\+?91[\s\-]?)?\b[6-9]\d{9}\b")
_LONG_NUMBER = re.compile(r"\b\d{6,}\b")


def mask(text: str) -> str:
    if not text:
        return ""
    out = _EMAIL.sub("<email>", text)
    out = _PHONE.sub("<phone>", out)
    out = _LONG_NUMBER.sub("<number>", out)
    return out
