#!/usr/bin/env bash
# Point Telegram at the deployed app.
#
#   ./scripts/set_webhook.sh https://safesaathi.onrender.com
#
# Reads TELEGRAM_BOT_TOKEN and TELEGRAM_SECRET from .env or the environment.
set -euo pipefail

BASE_URL="${1:-}"
if [[ -z "$BASE_URL" ]]; then
  echo "usage: $0 https://your-app.onrender.com"
  exit 1
fi

if [[ -f .env ]]; then
  # shellcheck disable=SC1091
  set -a && source .env && set +a
fi

: "${TELEGRAM_BOT_TOKEN:?set TELEGRAM_BOT_TOKEN in .env}"
SECRET="${TELEGRAM_SECRET:-change-me}"

curl -s "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/setWebhook" \
  --data-urlencode "url=${BASE_URL%/}/telegram/webhook" \
  --data-urlencode "secret_token=${SECRET}" \
  --data-urlencode 'allowed_updates=["message","edited_message","callback_query"]'
echo

curl -s "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/setMyCommands" \
  -H 'Content-Type: application/json' \
  -d '{"commands":[
        {"command":"start","description":"How SafeSaathi works"},
        {"command":"language","description":"Change the reply language"},
        {"command":"guardian","description":"Alert a family member about scams"},
        {"command":"link","description":"Enter a family link code"},
        {"command":"report","description":"Report a scam UPI ID, number or link"},
        {"command":"help","description":"Examples of what to forward"}]}'
echo

echo "--- webhook status ---"
curl -s "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getWebhookInfo"
echo
