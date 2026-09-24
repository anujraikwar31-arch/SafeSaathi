"""Family Guardian: a parent links one family member who gets alerted about scams.

The parent always starts the link, which is the consent step, and can undo it with
/unlink at any time.
"""
from __future__ import annotations

import random

from ..db import store

TEXT = {
    "en": {
        "code": ("Family Guardian is ready.\n\nAsk your son, daughter or a trusted family member "
                 "to open this bot and send:\n\n/link {code}\n\nThe code works for 30 minutes."),
        "linked_parent": "Done. {who} will now be alerted if you receive a likely scam.",
        "linked_guardian": ("You are now the Family Guardian for this person. "
                            "If a likely scam reaches them, you will get a message here."),
        "bad_code": "That code is wrong or has expired. Ask them to send /guardian again.",
        "unlinked": "Family Guardian is switched off for you.",
        "alert": ("Heads up: someone you protect just received a likely scam.\n\n"
                  "Message: {snippet}\n\nWhy: {reason}\n\nPlease call them before they reply or pay."),
    },
    "hi": {
        "code": ("फैमिली गार्जियन तैयार है।\n\nअपने बेटे, बेटी या भरोसेमंद सदस्य से कहें कि "
                 "इस बॉट पर यह भेजें:\n\n/link {code}\n\nयह कोड 30 मिनट तक चलेगा।"),
        "linked_parent": "हो गया। अब ठगी वाला मैसेज आने पर {who} को सूचना मिलेगी।",
        "linked_guardian": ("अब आप इस व्यक्ति के फैमिली गार्जियन हैं। ठगी वाला मैसेज आने पर "
                            "आपको यहीं जानकारी मिलेगी।"),
        "bad_code": "यह कोड गलत है या समय खत्म हो गया। उनसे दोबारा /guardian भेजने को कहें।",
        "unlinked": "आपके लिए फैमिली गार्जियन बंद कर दिया गया है।",
        "alert": ("ध्यान दें: जिनकी आप देखभाल करते हैं, उन्हें अभी ठगी वाला मैसेज मिला है।\n\n"
                  "मैसेज: {snippet}\n\nकारण: {reason}\n\nजवाब देने या पैसे भेजने से पहले उन्हें कॉल करें।"),
    },
}


def t(lang: str, key: str) -> str:
    return TEXT.get(lang, TEXT["en"]).get(key, TEXT["en"][key])


def start_link(chat_id: int, lang: str = "en") -> str:
    code = f"{random.randint(100000, 999999)}"
    store.set_link_code(chat_id, code)
    return t(lang, "code").format(code=code)


def complete_link(guardian_chat_id: int, code: str) -> tuple[bool, int | None]:
    parent = store.find_by_link_code(code.strip())
    if not parent or parent["chat_id"] == guardian_chat_id:
        return False, None
    store.link_guardian(parent["chat_id"], guardian_chat_id)
    return True, parent["chat_id"]


def guardian_of(chat_id: int) -> int | None:
    user = store.get_user(chat_id)
    return user.get("guardian_chat_id") if user else None


def alert_text(snippet: str, reason: str, lang: str = "en") -> str:
    return t(lang, "alert").format(snippet=snippet, reason=reason)
