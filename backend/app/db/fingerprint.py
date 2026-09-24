"""Turn a message into a template fingerprint.

Scammers send the same text to lakhs of people, changing only the numbers and the link.
Normalising those away means one check answers every copy.
"""
from __future__ import annotations

import hashlib
import re

_URL = re.compile(r"https?://\S+|www\.\S+", re.I)
_UPI = re.compile(r"[\w.\-]{2,64}@[a-zA-Z]{2,32}\b")
_DIGITS = re.compile(r"\d+")
_JUNK = re.compile(r"[^\w#<>ऀ-ॿঀ-৿஀-௿]+")


def normalise(text: str) -> str:
    t = (text or "").lower()
    t = _URL.sub("<url>", t)
    t = _UPI.sub("<id>", t)
    t = _DIGITS.sub("#", t)
    t = _JUNK.sub(" ", t)
    return " ".join(t.split())


def make(text: str) -> str:
    return hashlib.sha256(normalise(text).encode("utf-8")).hexdigest()[:16]


def snippet(text: str, length: int = 90) -> str:
    """What the dashboard is allowed to show: digits masked, cut short."""
    masked = re.sub(r"\d", "X", (text or "").strip())
    masked = " ".join(masked.split())
    return masked[:length] + ("..." if len(masked) > length else "")
