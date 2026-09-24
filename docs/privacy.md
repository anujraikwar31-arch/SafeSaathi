# Privacy

SafeSaathi reads people's messages, so the rule we set ourselves is: keep nothing we do not
need to answer the next person faster.

## What we store

| Stored | Why | Where |
| --- | --- | --- |
| A one-way fingerprint of the normalised text (SHA-256, first 16 characters) | Recognise the same scam template again | `templates` |
| The verdict, risk, category, reasons and advice | Answer a repeat instantly | `templates` |
| A snippet with every digit replaced by X, cut to 90 characters | Show what is trending on the dashboard | `templates` |
| Verdict, category, language, timing, source | Dashboard counts | `checks` |
| A hashed Telegram chat ID | Count unique users without keeping identities | `checks` |
| Telegram chat ID, language, guardian chat ID | Send replies and Family Guardian alerts | `users` |
| Reported UPI IDs, numbers and links | Community scam radar | `reports` |

## What we do not store

The original message. Screenshots and voice notes are processed in memory and dropped.

## Before anything leaves the server

`engine/mask.py` replaces email addresses, Indian mobile numbers and any run of six or more
digits (account numbers, card numbers, OTPs) before the text is sent to Gemini. Small amounts
such as Rs 499 stay, because they matter to the verdict. Links stay, because the link checks
need them.

This matters because the [Gemini API terms](https://ai.google.dev/gemini-api/terms) say that
on the unpaid tier Google may use prompts and responses to improve its products, that human
reviewers may read them, and that sensitive or personal information should not be sent. A real
launch would move to the paid tier, where prompts are not used for training; until then the
masking step and the demo-only usage are what keep this acceptable.

## Family Guardian consent

Only the parent can start a link, by sending `/guardian` and passing a 6-digit code to the
family member. The code expires in 30 minutes. Either side can end it with `/unlink`. The
alert carries a digit-masked snippet and one reason, not the full message.

## Data location and deletion

By default the database is SQLite inside the container, which is erased on every redeploy.
With `DATABASE_URL` set, rows live in your Postgres or Supabase project. To wipe everything,
delete the `safesaathi.db` file or truncate the five tables.
