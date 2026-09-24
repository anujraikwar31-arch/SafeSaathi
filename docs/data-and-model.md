# Data and model

## Where the data comes from

`ml/generate_seed.py` holds message **templates** the team wrote from public scam advisories,
news reports and messages on our own phones, with every real name, number and link replaced by
a slot. The generator fills the slots to produce rows.

- `ml/data/train.csv` - 499 rows (242 scam, 257 genuine) from 38 scam and 36 genuine templates.
- `ml/data/test_set.csv` - 112 rows (58 scam, 54 genuine) from 14 scam and 12 genuine templates
  that are **never** used for training and never appear in the Gemini prompt.
- `ml/data/collected.csv` - optional. Real messages the team collects during the pilot, with
  the same columns (`text,label,category,language,source`). If the file exists it is merged
  into training automatically, so the model improves as real samples arrive.

The two sets use different random seeds, so adding training templates never reshuffles the
test set.

Genuine messages matter as much as scams. The corpus deliberately contains bank OTP alerts
("do not share this OTP"), debit and credit alerts, delivery updates, bill receipts and
appointment confirmations, so the model does not learn that every message mentioning an OTP or
a rupee amount is a scam.

Two public datasets are credited for future training and are worth merging in once the team
has time: the [UCI SMS Spam Collection](https://archive.ics.uci.edu/dataset/228/sms+spam+collection)
(5,574 SMS, CC BY 4.0) and the [SMS Phishing Dataset by Mishra and Soni](https://data.mendeley.com/datasets/f45bkkt8pr/1)
(5,971 messages: 4,844 ham, 489 spam, 638 smishing). Both are mostly non-Indian SMS, which is
why our own templates carry more weight for now.

## The model

`ml/train.py` builds a scikit-learn pipeline:

- TF-IDF over word unigrams and bigrams, plus TF-IDF over character 3 to 5-grams. Character
  n-grams are what make it survive Hinglish spelling ("turant", "kaat diya", "paisa double").
- Logistic regression, `class_weight="balanced"`, 2000 iterations.
- Saved to `backend/models/scam_clf.joblib`, about 215 KB, loaded once at startup.

The 80/20 split printed during training always looks perfect, because both halves come from
the same templates. It is a smoke test, not a result. The real measure is
[evaluation.md](evaluation.md), which runs the held-out templates through the live API.

`classifier.top_words()` can list the words that pushed a score up, which is useful when
writing the "why" without Gemini.

## Retraining

```bash
python ml/generate_seed.py     # regenerates train.csv and test_set.csv, merges collected.csv
python ml/train.py             # retrains and overwrites the model file
python ml/evaluate.py --api http://localhost:8000
```

Keep the scikit-learn version in `backend/requirements.txt` equal to the version that trained
the model, otherwise loading the file warns or fails.

## Stretch: MuRIL

A fine-tuned `google/muril-base-cased` would handle Devanagari and code-mixed text better than
TF-IDF. It is roughly 900 MB in memory, which does not fit the free hosting tier, so the plan
is to fine-tune it in Colab, report its scores here, and serve it only if the project moves to
paid hosting.
