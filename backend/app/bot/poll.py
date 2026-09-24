"""Run the bot without a public URL (handy for a laptop demo):

    cd backend && python -m app.bot.poll
"""
from __future__ import annotations

import asyncio
import logging

import httpx

from ..config import settings
from ..db import store
from .telegram import API, handle_update

log = logging.getLogger("safesaathi.poll")


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    if not settings.has_telegram:
        raise SystemExit("Set TELEGRAM_BOT_TOKEN in .env first.")
    store.init_db()
    offset: int | None = None
    async with httpx.AsyncClient(timeout=70) as client:
        await client.get(f"{API}/deleteWebhook")
        log.info("polling for updates. Press Ctrl+C to stop.")
        while True:
            params: dict[str, object] = {"timeout": 50}
            if offset is not None:
                params["offset"] = offset
            try:
                data = (await client.get(f"{API}/getUpdates", params=params)).json()
            except Exception as exc:
                log.warning("getUpdates failed: %s", exc)
                await asyncio.sleep(3)
                continue
            for update in data.get("result", []):
                offset = update["update_id"] + 1
                await handle_update(update)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
