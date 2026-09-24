"""UPI IDs and phone numbers: what we can honestly check, and what we cannot."""
from __future__ import annotations

import re
from typing import Any

from ..db import store

# Handles used by the main UPI apps and banks. Add more from NPCI's app list.
KNOWN_HANDLES = {
    "oksbi", "okhdfcbank", "okicici", "okaxis", "ybl", "ibl", "axl", "apl", "yapl",
    "paytm", "ptsbi", "ptyes", "pthdfc", "ptaxis", "upi", "kotak", "kmbl", "icici",
    "sbi", "hdfcbank", "axisbank", "barodampay", "cnrb", "pnb", "idfcbank", "indus",
    "fbl", "federal", "jupiteraxis", "superyes", "abfspay", "timecosmos", "waaxis",
}

_UPI_RE = re.compile(r"\b([a-z0-9][\w.\-]{1,63})@([a-z]{2,32})\b", re.I)
_PHONE_RE = re.compile(r"(?:\+?91[\s\-]?)?\b([6-9]\d{9})\b")
_EMAIL_TLDS = {"com", "in", "org", "net", "co", "io", "gov", "edu", "me"}


def find_upi_ids(text: str) -> list[str]:
    out = []
    for match in _UPI_RE.finditer(text or ""):
        handle = match.group(2).lower()
        if handle in _EMAIL_TLDS:          # that was an email address, not a UPI ID
            continue
        value = f"{match.group(1)}@{handle}".lower()
        if value not in out:
            out.append(value)
    return out[:5]


def find_phones(text: str) -> list[str]:
    out = []
    for match in _PHONE_RE.finditer(text or ""):
        if match.group(1) not in out:
            out.append(match.group(1))
    return out[:5]


def check(text: str) -> dict[str, Any]:
    upi_ids = find_upi_ids(text)
    phones = find_phones(text)
    notes: list[str] = []
    reported = 0

    for upi_id in upi_ids:
        handle = upi_id.split("@")[1]
        count = store.count_reports("upi", upi_id)
        reported += count
        if count:
            notes.append(f"This UPI ID has been reported {count} time(s) by other users.")
        elif handle not in KNOWN_HANDLES:
            notes.append(f"The UPI handle @{handle} is not one of the common bank or app handles.")

    for phone in phones:
        count = store.count_reports("phone", phone)
        reported += count
        if count:
            notes.append(f"This number has been reported {count} time(s) by other users.")

    return {"upi_ids": upi_ids, "phones": phones, "notes": notes[:2], "reported_before": reported}


HONEST_NOTE_EN = ("We cannot see who owns a UPI ID. Never pay to receive money, "
                  "and never enter your PIN for an incoming payment.")
HONEST_NOTE_HI = ("किसी यूपीआई आईडी का मालिक कौन है, यह हम नहीं देख सकते। "
                  "पैसे लेने के लिए कभी पिन न डालें।")
