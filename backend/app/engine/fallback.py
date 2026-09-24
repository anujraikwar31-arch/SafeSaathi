"""The answer we give when Gemini is not available: rules, links and the classifier.

It is deliberately plain. The demo keeps working with no API key at all, which also
makes the whole pipeline testable offline.
"""
from __future__ import annotations

from typing import Any

from . import links as links_mod
from . import rules as rules_mod
from . import upi as upi_mod

ADVICE = {
    "SCAM": {
        "en": "Do not reply, click or pay. Block the sender and report it on 1930 or cybercrime.gov.in.",
        "hi": "जवाब न दें, लिंक न खोलें और पैसे न भेजें। नंबर ब्लॉक करें और 1930 पर शिकायत करें।",
    },
    "SUSPICIOUS": {
        "en": "Do not act on this yet. Check with the company or bank on a number you already trust.",
        "hi": "अभी कुछ न करें। बैंक या कंपनी के भरोसेमंद नंबर पर खुद जाँच करें।",
    },
    "SAFE": {
        "en": "Nothing here looks like a scam, but never share an OTP or PIN with anyone.",
        "hi": "इसमें ठगी जैसा कुछ नहीं दिखा, फिर भी ओटीपी या पिन किसी को न बताएं।",
    },
}

NOTHING_FOUND = {
    "en": "No pressure, no money request and no risky link found in this message.",
    "hi": "इस मैसेज में न जल्दबाज़ी है, न पैसे की मांग और न कोई खतरनाक लिंक मिला।",
}

UNREADABLE = {
    "en": "We could not read this file. Please paste the text of the message instead.",
    "hi": "हम यह फ़ाइल नहीं पढ़ सके। कृपया मैसेज का टेक्स्ट भेजें।",
}


def build(hits: list[str], link_signals: list[dict[str, Any]], upi_info: dict[str, Any],
          classifier_score: float | None, verdict: str, lang: str = "en") -> dict[str, Any]:
    reasons: list[str] = []
    reasons += rules_mod.reasons(hits, lang)
    reasons += links_mod.link_reasons(link_signals, lang)
    if len(reasons) < 3:
        reasons += upi_info.get("notes", [])
    reasons = [r for r in reasons if r][:3]

    if verdict == "SAFE":
        # A safe answer should not list scary reasons. Say plainly that nothing was found.
        reasons = [NOTHING_FOUND.get(lang, NOTHING_FOUND["en"])]
    elif not reasons:
        if upi_info.get("upi_ids"):
            reasons = [upi_mod.HONEST_NOTE_HI if lang == "hi" else upi_mod.HONEST_NOTE_EN]
        else:
            reasons = [
                "This message reads like other scam messages people have reported."
                if lang != "hi"
                else "यह मैसेज उन ठगी वाले मैसेज जैसा लगता है जिनकी शिकायत हुई है।"
            ]

    category = rules_mod.category_for(hits)
    if not category:
        worst_link = links_mod.worst(link_signals)
        if worst_link and (worst_link.get("lookalike") or worst_link.get("safe_browsing")):
            category = "other_scam"
        elif upi_info.get("upi_ids") and verdict != "SAFE":
            category = "upi_cashback_collect"
        else:
            category = "other_scam" if verdict != "SAFE" else "not_scam"

    advice = ADVICE[verdict].get(lang, ADVICE[verdict]["en"])
    if upi_info.get("upi_ids") and verdict != "SAFE":
        note = upi_mod.HONEST_NOTE_HI if lang == "hi" else upi_mod.HONEST_NOTE_EN
        advice = f"{advice} {note}"
    return {"reasons": reasons, "category": category, "advice": advice}
