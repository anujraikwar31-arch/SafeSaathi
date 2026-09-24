"""Telegram bot: webhook route plus the handlers, used by the webhook and the poller."""
from __future__ import annotations

import base64
import logging
from html import escape
from typing import Any

import httpx
from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request

from ..config import LANGUAGES, settings
from ..db import fingerprint as fp_mod
from ..db import store
from ..pipeline import analyze
from . import guardian

log = logging.getLogger("safesaathi.bot")
router = APIRouter(tags=["telegram"])

API = f"https://api.telegram.org/bot{settings.telegram_bot_token}"
FILE_API = f"https://api.telegram.org/file/bot{settings.telegram_bot_token}"

HEAD = {
    "SCAM": {"en": "🔴 SCAM", "hi": "🔴 धोखाधड़ी"},
    "SUSPICIOUS": {"en": "🟠 SUSPICIOUS", "hi": "🟠 संदिग्ध"},
    "SAFE": {"en": "🟢 LOOKS SAFE", "hi": "🟢 सुरक्षित लगता है"},
}
WHAT_TO_DO = {"en": "What to do", "hi": "क्या करें"}
SEEN = {"en": "Checked {n} times on SafeSaathi.", "hi": "सेफ़साथी पर यह मैसेज {n} बार जांचा जा चुका है।"}
HELPLINE = {"en": "Cyber fraud helpline: 1930", "hi": "साइबर ठगी हेल्पलाइन: 1930"}

WELCOME = {
    "en": ("Hello! I am SafeSaathi.\n\nNot sure if a message is a scam? Forward it to me.\n\n"
           "You can send me:\n• any text or SMS\n• a screenshot\n• a link or a UPI ID\n• a voice note\n\n"
           "I will tell you if it is safe, suspicious or a scam, and why.\n\n"
           "/language to change language\n/guardian to alert a family member about scams\n/help for examples"),
    "hi": ("नमस्ते! मैं सेफ़साथी हूँ।\n\nकोई मैसेज ठगी है या नहीं, यह जानना है? उसे मुझे फॉरवर्ड करें।\n\n"
           "आप भेज सकते हैं:\n• कोई भी टेक्स्ट या एसएमएस\n• स्क्रीनशॉट\n• लिंक या यूपीआई आईडी\n• वॉइस नोट\n\n"
           "मैं बताऊंगा कि यह सुरक्षित है, संदिग्ध है या ठगी, और क्यों।\n\n"
           "/language भाषा बदलने के लिए\n/guardian परिवार को सूचना देने के लिए\n/help उदाहरण के लिए"),
}
HELP = {
    "en": ("Try forwarding messages like these:\n\n"
           "• \"Dear consumer, your electricity will be cut tonight at 9:30 PM. Call officer 98XXXXXX21.\"\n"
           "• \"Your KYC has expired. Update now: kyc-update-bnk.in\"\n"
           "• \"Earn Rs 5,000 daily by liking videos. Pay Rs 499 to register.\"\n\n"
           "Or send a screenshot of a WhatsApp chat, a link, or a UPI ID.\n"
           "Report a scam UPI ID or number with: /report 98XXXXXXXX"),
    "hi": ("इन जैसे मैसेज फॉरवर्ड करके देखें:\n\n"
           "• \"आपकी बिजली आज रात 9:30 बजे काट दी जाएगी। अधिकारी को कॉल करें।\"\n"
           "• \"आपका केवाईसी खत्म हो गया है। अभी अपडेट करें: kyc-update-bnk.in\"\n"
           "• \"वीडियो लाइक करके रोज़ 5,000 रुपये कमाएं। 499 रुपये देकर रजिस्टर करें।\"\n\n"
           "या व्हाट्सएप चैट का स्क्रीनशॉट, लिंक या यूपीआई आईडी भेजें।\n"
           "ठगी वाली यूपीआई आईडी या नंबर की शिकायत: /report 98XXXXXXXX"),
}


# ----------------------------------------------------------------- transport

async def call(method: str, **payload: Any) -> dict[str, Any]:
    if not settings.has_telegram:
        return {}
    async with httpx.AsyncClient(timeout=25) as client:
        response = await client.post(f"{API}/{method}", json=payload)
        return response.json()


async def send_message(chat_id: int, text: str, buttons: list[list[dict]] | None = None) -> None:
    payload: dict[str, Any] = {"chat_id": chat_id, "text": text, "parse_mode": "HTML",
                               "disable_web_page_preview": True}
    if buttons:
        payload["reply_markup"] = {"inline_keyboard": buttons}
    await call("sendMessage", **payload)


async def send_voice(chat_id: int, audio_b64: str) -> None:
    if not settings.has_telegram:
        return
    async with httpx.AsyncClient(timeout=40) as client:
        await client.post(f"{API}/sendVoice", data={"chat_id": str(chat_id)},
                          files={"voice": ("reply.mp3", base64.b64decode(audio_b64), "audio/mpeg")})


async def download(file_id: str) -> bytes | None:
    try:
        async with httpx.AsyncClient(timeout=40) as client:
            info = (await client.get(f"{API}/getFile", params={"file_id": file_id})).json()
            path = info["result"]["file_path"]
            return (await client.get(f"{FILE_API}/{path}")).content
    except Exception as exc:
        log.warning("download failed: %s", exc)
        return None


# ------------------------------------------------------------------ replies

def verdict_text(result: dict[str, Any], lang: str) -> str:
    head = HEAD[result["verdict"]].get(lang, HEAD[result["verdict"]]["en"])
    lines = [f"<b>{head}</b>  ({result['risk']}/100)", ""]
    lines += [f"• {escape(reason)}" for reason in result["reasons"]]
    lines += ["", f"<b>{WHAT_TO_DO.get(lang, WHAT_TO_DO['en'])}:</b> {escape(result['advice'])}"]
    lines.append(HELPLINE.get(lang, HELPLINE["en"]))
    if result.get("seen_count", 1) > 1:
        lines += ["", SEEN.get(lang, SEEN["en"]).format(n=result["seen_count"])]
    return "\n".join(lines)


def verdict_buttons(result: dict[str, Any]) -> list[list[dict]]:
    buttons = [[{"text": "Report on cybercrime.gov.in", "url": "https://cybercrime.gov.in"}]]
    if result.get("fingerprint"):
        buttons.append([{"text": "This answer looks wrong",
                         "callback_data": f"fb:{result['fingerprint']}"}])
    return buttons


async def reply_with_verdict(chat_id: int, result: dict[str, Any], lang: str) -> None:
    await send_message(chat_id, verdict_text(result, lang), verdict_buttons(result))
    if result.get("audio_b64"):
        await send_voice(chat_id, result["audio_b64"])
    if result["verdict"] == "SCAM":
        guardian_id = guardian.guardian_of(chat_id)
        if guardian_id:
            reason = result["reasons"][0] if result["reasons"] else ""
            await send_message(guardian_id, escape(guardian.alert_text(
                fp_mod.snippet(result.get("extracted_text", ""), 120), reason, lang)))


# ----------------------------------------------------------------- commands

async def handle_command(chat_id: int, text: str, lang: str) -> None:
    command, _, argument = text.partition(" ")
    command = command.split("@")[0].lower()
    argument = argument.strip()

    if command in ("/start", "/help"):
        body = WELCOME if command == "/start" else HELP
        await send_message(chat_id, body.get(lang, body["en"]))
    elif command == "/language":
        buttons = [[{"text": name, "callback_data": f"lang:{code}"}]
                   for code, name in LANGUAGES.items()]
        await send_message(chat_id, "Choose a language / भाषा चुनें", buttons)
    elif command == "/guardian":
        await send_message(chat_id, guardian.start_link(chat_id, lang))
    elif command == "/link":
        ok, parent_id = guardian.complete_link(chat_id, argument)
        if ok:
            await send_message(chat_id, guardian.t(lang, "linked_guardian"))
            if parent_id:
                parent_lang = (store.get_user(parent_id) or {}).get("lang", "en")
                await send_message(parent_id, guardian.t(parent_lang, "linked_parent")
                                   .format(who="Your family member"))
        else:
            await send_message(chat_id, guardian.t(lang, "bad_code"))
    elif command == "/unlink":
        store.unlink_guardian(chat_id)
        await send_message(chat_id, guardian.t(lang, "unlinked"))
    elif command == "/report":
        if not argument:
            await send_message(chat_id, "Send it like this: /report 98XXXXXXXX or /report name@okaxis")
            return
        kind = "upi" if "@" in argument else ("url" if "." in argument else "phone")
        count = store.add_report(kind, argument, "telegram")
        await send_message(chat_id, f"Thank you. {escape(argument)} has now been reported {count} time(s).")
    elif command == "/stats":
        data = store.stats()
        await send_message(chat_id, f"Checks so far: {data['total_checks']}\n"
                                    f"Scams and suspicious: {data['scam_share']}%")
    else:
        await send_message(chat_id, HELP.get(lang, HELP["en"]))


async def handle_callback(callback: dict[str, Any]) -> None:
    data = callback.get("data", "")
    chat_id = callback["message"]["chat"]["id"]
    await call("answerCallbackQuery", callback_query_id=callback["id"])
    if data.startswith("lang:"):
        code = data.split(":", 1)[1]
        if code in LANGUAGES:
            store.set_user_lang(chat_id, code)
            await send_message(chat_id, f"Language set to {LANGUAGES[code]}.")
    elif data.startswith("fb:"):
        store.add_feedback(data.split(":", 1)[1], says_scam=False, source="telegram")
        await send_message(chat_id, "Thank you. A human will look at this message.")


# ------------------------------------------------------------------ updates

async def handle_update(update: dict[str, Any]) -> None:
    try:
        if "callback_query" in update:
            await handle_callback(update["callback_query"])
            return
        message = update.get("message") or update.get("edited_message") or {}
        chat_id = (message.get("chat") or {}).get("id")
        if not chat_id:
            return

        user = store.ensure_user(chat_id)
        lang = user.get("lang") or settings.default_lang
        text = message.get("text") or message.get("caption") or ""

        if text.startswith("/"):
            await handle_command(chat_id, text, lang)
            return

        await call("sendChatAction", chat_id=chat_id, action="typing")

        if "photo" in message:
            data = await download(message["photo"][-1]["file_id"])
            result = await analyze("image", text, data, "image/jpeg", lang, "telegram",
                                   str(chat_id), True)
        elif "voice" in message or "audio" in message:
            blob = message.get("voice") or message.get("audio")
            data = await download(blob["file_id"])
            result = await analyze("audio", "", data, blob.get("mime_type", "audio/ogg"),
                                   lang, "telegram", str(chat_id), True)
        elif "document" in message and str(message["document"].get("mime_type", "")).startswith("image/"):
            data = await download(message["document"]["file_id"])
            result = await analyze("image", text, data, message["document"]["mime_type"],
                                   lang, "telegram", str(chat_id), True)
        elif text.strip():
            result = await analyze("text", text, None, None, lang, "telegram", str(chat_id), True)
        else:
            await send_message(chat_id, HELP.get(lang, HELP["en"]))
            return

        await reply_with_verdict(chat_id, result, lang)
    except Exception as exc:                       # never leave the user without an answer
        log.exception("update failed: %s", exc)
        try:
            chat_id = ((update.get("message") or {}).get("chat") or {}).get("id")
            if chat_id:
                await send_message(chat_id, "Sorry, I could not check that. "
                                            "Please send the text or a screenshot again.")
        except Exception:
            pass


@router.post("/telegram/webhook")
async def webhook(request: Request, tasks: BackgroundTasks,
                  x_telegram_bot_api_secret_token: str = Header(default="")) -> dict[str, bool]:
    if settings.telegram_secret and x_telegram_bot_api_secret_token != settings.telegram_secret:
        raise HTTPException(status_code=403, detail="bad secret")
    update = await request.json()
    tasks.add_task(handle_update, update)          # answer Telegram at once
    return {"ok": True}
