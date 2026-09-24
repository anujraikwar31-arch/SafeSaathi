# API

Interactive docs are at `/docs` on any running instance.

## POST /api/analyze

`multipart/form-data`, so the same call works for text and for files.

| Field | Values | Notes |
| --- | --- | --- |
| `kind` | `text`, `image`, `audio`, `link`, `upi` | what the user sent |
| `content` | string | the text, link or UPI ID; empty for image and audio |
| `file` | file | screenshot (jpg, png) or voice note (ogg, mp3) |
| `lang` | `en`, `hi`, `ta`, `bn`, `mr`, `te` | language of reasons, advice and voice |
| `source` | `web`, `telegram`, `test` | `test` skips the cache and is hidden from the dashboard |
| `user_ref` | string | Telegram chat ID; hashed before storage |
| `want_audio` | `true`, `false` | return an MP3 voice reply as base64 |

```bash
curl -X POST http://localhost:8000/api/analyze \
  -F kind=text \
  -F "content=Your KYC has expired, account will be blocked today. Update at http://kyc-update-bnk.in" \
  -F lang=en -F want_audio=false
```

```json
{
  "verdict": "SCAM",
  "risk": 100,
  "category": "kyc_account_block",
  "reasons": [
    "Talks about KYC or Aadhaar updates, a common bank-scam trick.",
    "Threatens to block or freeze your account.",
    "The link kyc-update-bnk.in uses the name 'bnk' but is not an official site."
  ],
  "advice": "Do not reply, click or pay. Block the sender and report it on 1930 or cybercrime.gov.in.",
  "extracted_text": "Your KYC has expired ...",
  "signals": {
    "rules": ["kyc", "account_block", "urgency"],
    "classifier": 0.97,
    "gemini_risk": null,
    "engine": "fallback",
    "links": [{"url": "http://kyc-update-bnk.in", "domain": "kyc-update-bnk.in",
               "shortened": false, "age_days": null, "lookalike": "...",
               "risky_tld": false, "safe_browsing": false}],
    "upi_ids": [], "phones": [], "reported_before": 0
  },
  "seen_count": 3,
  "cached": false,
  "fingerprint": "3f9a1c0d7b2e4a61",
  "audio_b64": null,
  "lang": "en",
  "latency_ms": 284
}
```

`verdict` is `SAFE`, `SUSPICIOUS` or `SCAM`. `risk` is 0 to 100. `signals.engine` is `gemini`,
`fallback` or `cache`, so you can always tell what answered.

Categories: `kyc_account_block`, `electricity_bill`, `parcel_digital_arrest`, `job_task`,
`investment`, `upi_cashback_collect`, `lottery_prize`, `loan_app`, `fake_payment`,
`relative_emergency`, `other_scam`, `not_scam`.

## GET /api/stats

Numbers for the dashboard: totals, split by verdict, counts by category, checks per day for a
week, the ten most-seen non-safe templates, languages used. Test traffic is excluded.

## POST /api/feedback

```json
{"fingerprint": "3f9a1c0d7b2e4a61", "says_scam": false, "source": "web"}
```

## POST /api/report

```json
{"kind": "upi", "value": "winner2026@ybl", "source": "web"}
```

`kind` is `upi`, `phone` or `url`. Reported values raise the risk of later messages that
contain them, which is the community scam radar.

## POST /telegram/webhook

Called by Telegram. Requires the `X-Telegram-Bot-Api-Secret-Token` header to match
`TELEGRAM_SECRET`. Returns immediately and processes the update in the background, so
Telegram never retries a slow check and users never get double replies.

## GET /health

`{"ok": true, "gemini": false, "classifier": true, "telegram": true}` - useful for the
uptime pinger and for knowing which engine is live.
