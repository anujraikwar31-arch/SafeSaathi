# Architecture

One FastAPI service holds everything: the check pipeline, the Telegram webhook and the static
web app. The bot calls the pipeline in-process, so there is a single deployment and a single
place where a verdict is decided.

```
                    ┌──────────────────────────── one Docker image ───────────────────────────┐
 Telegram  ──webhook┤  bot/telegram.py ─┐                                                      │
                    │                   ├─→ pipeline.analyze() ─→ verdict ─→ reply + voice     │
 Web app  ──fetch───┤  main.py routes ──┘        │                                             │
 (served by the     │                            ├─ engine/rules.py        red flags           │
  same service)     │                            ├─ engine/links.py        domains, RDAP, GSB  │
                    │                            ├─ engine/upi.py          UPI, phones         │
                    │                            ├─ engine/classifier.py   TF-IDF + logreg     │
                    │                            ├─ engine/llm.py          Gemini, JSON schema │
                    │                            ├─ engine/ocr.py          Tesseract fallback  │
                    │                            ├─ engine/tts.py          gTTS voice reply    │
                    │                            └─ db/store.py            SQLite or Postgres  │
                    └──────────────────────────────────────────────────────────────────────────┘
```

## Request flow

1. `POST /api/analyze` accepts multipart form data, so text and files use the same endpoint.
2. **Read.** Screenshots and voice notes go to Gemini, which transcribes and judges in one
   call to save quota. With no key, images go through Tesseract OCR; voice notes are declined
   politely.
3. **Fingerprint and cache.** `db/fingerprint.py` lowercases the text, replaces links, IDs and
   digits, and hashes the result. A hit returns the stored verdict in milliseconds and raises
   the template's counter, which also drives the trending list.
4. **Fast checks** run concurrently with short timeouts (`asyncio.gather`): rules, link
   checks, UPI checks, classifier. Any of them may fail; a failed check is left out of the
   evidence rather than breaking the answer.
5. **Gemini** receives the masked message plus the findings, and must reply in a fixed JSON
   schema. Message text is wrapped in `<message>` tags and the system prompt says never to
   follow instructions found inside it.
6. **Combine** turns the signals into one 0 to 100 risk score, with hard overrides for Safe
   Browsing hits, lookalike domains and hard red-flag rules.
7. **Store and answer.** The template, verdict and masked snippet are saved, the check is
   logged for the dashboard, and the reply goes out with buttons, and a voice note when asked.

## Why these choices

- **One service.** Fewer moving parts to break on deadline day, and the bot avoids an extra
  network hop per message.
- **Evidence first, model second.** Rules and link checks are deterministic and explainable.
  Gemini is asked to reason *with* that evidence, which keeps reasons concrete.
- **Everything optional.** No Gemini key, no Safe Browsing key, no Postgres, no Telegram token:
  the app still starts and still answers. That is what makes it demo-proof.
- **Template fingerprints.** Scams are mass-produced. Normalising numbers and links means one
  full check answers every later copy, which is also why cost per check falls as usage grows.
