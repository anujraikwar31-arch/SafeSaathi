# Limitations

Things we would rather state plainly than be caught on.

**We cannot see who owns a UPI ID or a phone number.** There is no public registry. We check
the handle against the common bank and app handles, count community reports, and read the
context of the message. The reply says this out loud rather than pretending certainty.

**Voice notes need Gemini.** Speech-to-text is not bundled. Without an API key the bot asks for
text or a screenshot instead. Offline Whisper is possible but does not fit free hosting.

**Screenshot reading is only as good as the image.** Tesseract handles clean chat screenshots;
blurry photos of a screen, heavy stylisation or mixed scripts can produce poor text. Gemini
does much better, which is why it is the first choice when a key is present.

**The dataset is seeded by us.** The templates come from public advisories, news reports and
our own inboxes, and the test set uses different wording, but it is still our writing. Real
inboxes will contain scams no one on the team has thought of. `ml/data/collected.csv` exists so
real samples can be merged in continuously.

**A confident scam can still slip through.** A well-written message with no link, no urgency
and no money request, such as slow-building investment grooming, is hard for any system. The
three-level verdict exists so the honest answer can be "suspicious" instead of a wrong "safe".

**False alarms are possible.** Genuine bank messages use the same words as scams. That is why
nothing is ever blocked automatically, every verdict shows its reasons, and a "this answer
looks wrong" button feeds `/api/feedback`.

**Free-tier limits.** Gemini's free tier is rate limited per minute and per day. The cache,
the fallback path and spacing the evaluation runs keep us inside it. A free Render service
sleeps after 15 minutes of inactivity and takes about a minute to wake.

**Not a substitute for reporting.** SafeSaathi tells you what a message looks like. Money
already sent has to go to the 1930 helpline or cybercrime.gov.in, fast; the reply always says
so.
