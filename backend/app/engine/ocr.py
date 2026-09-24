"""Offline text extraction from screenshots, used when Gemini is not configured.

Tesseract is installed in the Docker image (English plus Hindi). If it is missing,
the function returns an empty string and the app asks the user to paste the text.
"""
from __future__ import annotations

import io
import logging

log = logging.getLogger("safesaathi.ocr")


def available() -> bool:
    try:
        import pytesseract  # noqa: F401
        from PIL import Image  # noqa: F401
        import shutil
        return shutil.which("tesseract") is not None
    except Exception:
        return False


def read_image(data: bytes) -> str:
    if not data or not available():
        return ""
    try:
        import pytesseract
        from PIL import Image
        image = Image.open(io.BytesIO(data))
        if image.mode != "RGB":
            image = image.convert("RGB")
        text = pytesseract.image_to_string(image, lang="eng+hin")
        return " ".join(text.split())
    except Exception as exc:
        log.warning("ocr failed: %s", exc)
        return ""
