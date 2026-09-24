# Deploy

One Docker image serves the API, the web app, the dashboard and the Telegram webhook.
Budget: 15 minutes.

## 1. Push the code

```bash
git init && git add . && git commit -m "SafeSaathi"
git branch -M main
git remote add origin <your github repo>
git push -u origin main
```

Make sure `.env` is **not** committed. `.gitignore` already excludes it.

## 2. Deploy on Render (free)

1. render.com, New, **Web Service**, connect the repo.
2. Runtime **Docker**. Dockerfile path `./Dockerfile`. Instance type **Free**.
   (Or New, **Blueprint**, which reads `render.yaml`.)
3. Health check path: `/health`.
4. Environment variables (Settings, Environment):

   | Key | Value |
   | --- | --- |
   | `GEMINI_API_KEY` | from aistudio.google.com, optional but recommended |
   | `GEMINI_MODEL` | the model code shown in AI Studio, e.g. a current Flash model |
   | `TELEGRAM_BOT_TOKEN` | from @BotFather |
   | `TELEGRAM_SECRET` | any random string |
   | `SAFE_BROWSING_KEY` | optional |
   | `DATABASE_URL` | optional, a Supabase pooler URL for data that survives redeploys |
   | `CORS_ORIGINS` | `*` while judging |

5. Deploy, then open `https://<your-app>.onrender.com/health`. It should say `{"ok": true}`.

**Keep it awake.** A free Render service sleeps after 15 minutes without traffic and takes about
a minute to wake. Add a free monitor (uptimerobot.com or cron-job.org) that hits `/health`
every 10 minutes.

**Data.** With no `DATABASE_URL` the app writes to SQLite inside the container, which is wiped
on every deploy. For the demo that is fine; for numbers that survive, create a free Supabase
project, copy the **pooler** connection string into `DATABASE_URL`, and redeploy. The tables
are created automatically on startup.

## 3. Point Telegram at it

```bash
./scripts/set_webhook.sh https://<your-app>.onrender.com
```

That sets the webhook with the secret and registers the bot commands. The script prints
`getWebhookInfo` at the end; `"pending_update_count": 0` and no `last_error_message` means it
is working. Message your bot and send it a scam text.

No public URL yet? Run the bot from a laptop instead:

```bash
cd backend && python -m app.bot.poll
```

## 4. Check everything

```bash
python scripts/smoke_test.py --api https://<your-app>.onrender.com
python ml/evaluate.py --api https://<your-app>.onrender.com --sleep 7   # free Gemini tier
```

`smoke_test.py` runs ten known messages plus the cache and report paths and prints FAILURES at
the end. `evaluate.py` rewrites `docs/evaluation.md` with the numbers of that deployment.

## 5. Before you submit

- [ ] Open the web app on a phone, in an incognito window.
- [ ] Message the bot from a Telegram account that has never used it.
- [ ] Check `/dashboard` shows real checks.
- [ ] Put the live links at the top of `README.md`.
- [ ] Rerun `ml/evaluate.py` against the deployment and paste the numbers into the deck.
