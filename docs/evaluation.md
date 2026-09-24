# Evaluation

Run against `http://localhost:8000` with the engine reported as **rules+classifier**, on 112 held-out messages (58 scam, 54 genuine) whose wording never appears in training data or in the prompt.

| Measure | Result |
| --- | --- |
| Messages tested | 112 |
| Scam messages caught (scam or suspicious) | 100.0% |
| Scam messages called Scam outright | 51.7% |
| Genuine messages wrongly flagged | 0.0% |
| Precision on flagged messages | 100.0% |
| Overall accuracy | 100.0% |
| Median time per check | 0.01 s |
| Slowest check | 0.31 s |

Confusion matrix: true positives 58, false negatives 0, false positives 0, true negatives 54.

## What this number does not prove

The seed test set is made of message templates the team wrote from public scam advisories,
news reports and messages on our own phones. It measures whether the system generalises to
wording it has never seen, but it is still our own writing, so real inboxes will be harder.
Replace `ml/data/test_set.csv` with real forwarded messages as the pilot collects them and
run this script again before quoting a number anywhere.
