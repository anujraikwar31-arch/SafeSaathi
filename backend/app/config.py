"""Settings. Reads a .env file if present, otherwise plain environment variables."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]      # .../backend
REPO_DIR = BACKEND_DIR.parent                          # repo root


def _load_dotenv() -> None:
    for path in (REPO_DIR / ".env", BACKEND_DIR / ".env"):
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv()


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


@dataclass(frozen=True)
class Settings:
    # AI
    gemini_api_key: str = _env("GEMINI_API_KEY")
    gemini_model: str = _env("GEMINI_MODEL", "gemini-2.5-flash")
    # Telegram
    telegram_bot_token: str = _env("TELEGRAM_BOT_TOKEN")
    telegram_secret: str = _env("TELEGRAM_SECRET", "change-me")
    # Optional link reputation
    safe_browsing_key: str = _env("SAFE_BROWSING_KEY")
    # Storage
    database_url: str = _env("DATABASE_URL", f"sqlite:///{BACKEND_DIR / 'safesaathi.db'}")
    # Web
    public_base_url: str = _env("PUBLIC_BASE_URL", "http://localhost:8000")
    cors_origins: str = _env("CORS_ORIGINS", "*")
    default_lang: str = _env("DEFAULT_LANG", "en")
    enable_tts: bool = _env("ENABLE_TTS", "true").lower() != "false"

    @property
    def has_gemini(self) -> bool:
        return bool(self.gemini_api_key)

    @property
    def has_telegram(self) -> bool:
        return bool(self.telegram_bot_token)


settings = Settings()

# Languages the bot and web app offer. gTTS codes are the same strings.
LANGUAGES = {
    "en": "English",
    "hi": "Hindi",
    "ta": "Tamil",
    "bn": "Bengali",
    "mr": "Marathi",
    "te": "Telugu",
}

CATEGORIES = [
    "kyc_account_block",
    "electricity_bill",
    "parcel_digital_arrest",
    "job_task",
    "investment",
    "upi_cashback_collect",
    "lottery_prize",
    "loan_app",
    "fake_payment",
    "relative_emergency",
    "other_scam",
    "not_scam",
]

CATEGORY_LABELS = {
    "kyc_account_block": "KYC or account block",
    "electricity_bill": "Electricity bill",
    "parcel_digital_arrest": "Parcel or digital arrest",
    "job_task": "Task-based job",
    "investment": "Investment or trading",
    "upi_cashback_collect": "UPI cashback or collect request",
    "lottery_prize": "Lottery or prize",
    "loan_app": "Instant loan app",
    "fake_payment": "Fake payment proof",
    "relative_emergency": "Relative in trouble",
    "other_scam": "Other scam",
    "not_scam": "No scam found",
}
