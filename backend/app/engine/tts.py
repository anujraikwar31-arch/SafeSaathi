"""Voice replies with gTTS. Optional: if it fails, the text reply still goes out."""
from __future__ import annotations

import base64
import io
import logging

from ..config import settings

log = logging.getLogger("safesaathi.tts")

VERDICT_LINE = {
    "SCAM": {"en": "This message looks like a scam.",
             "hi": "यह मैसेज धोखाधड़ी लगता है।",
             "ta": "இந்த செய்தி மோசடி போல் தெரிகிறது.",
             "bn": "এই বার্তাটি প্রতারণার মতো মনে হচ্ছে।",
             "mr": "हा संदेश फसवणूक वाटतो.",
             "te": "ఈ సందేశం మోసంలా కనిపిస్తోంది."},
    "SUSPICIOUS": {"en": "Be careful. This message is suspicious.",
                   "hi": "सावधान रहें। यह मैसेज संदिग्ध है।",
                   "ta": "கவனமாக இருங்கள். இந்த செய்தி சந்தேகத்திற்குரியது.",
                   "bn": "সাবধান। এই বার্তাটি সন্দেহজনক।",
                   "mr": "सावध राहा. हा संदेश संशयास्पद आहे.",
                   "te": "జాగ్రత్తగా ఉండండి. ఈ సందేశం అనుమానాస్పదం."},
    "SAFE": {"en": "This message looks safe.",
             "hi": "यह मैसेज सुरक्षित लगता है।",
             "ta": "இந்த செய்தி பாதுகாப்பானதாக தெரிகிறது.",
             "bn": "এই বার্তাটি নিরাপদ মনে হচ্ছে।",
             "mr": "हा संदेश सुरक्षित वाटतो.",
             "te": "ఈ సందేశం సురక్షితంగా కనిపిస్తోంది."},
}


def spoken_script(verdict: str, reasons: list[str], advice: str, lang: str) -> str:
    head = VERDICT_LINE.get(verdict, VERDICT_LINE["SUSPICIOUS"]).get(
        lang, VERDICT_LINE.get(verdict, VERDICT_LINE["SUSPICIOUS"])["en"])
    body = " ".join(reasons[:2])
    return " ".join(part for part in [head, body, advice] if part)[:600]


def speak(text: str, lang: str = "en") -> str | None:
    """Return an MP3 as base64, or None if speech is off or unavailable."""
    if not settings.enable_tts or not text.strip():
        return None
    try:
        from gtts import gTTS
        buffer = io.BytesIO()
        gTTS(text=text, lang=lang if lang in {"en", "hi", "ta", "bn", "mr", "te"} else "en").write_to_fp(buffer)
        return base64.b64encode(buffer.getvalue()).decode("ascii")
    except Exception as exc:
        log.warning("tts failed: %s", exc)
        return None
