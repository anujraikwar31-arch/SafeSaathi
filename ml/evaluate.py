"""Measure the whole system, not just the model.

Sends every message in the held-out test set to a running API and reports how many
scams were caught, how many genuine messages were wrongly flagged, and how long a
check takes.

    python ml/evaluate.py --api http://localhost:8000 --sleep 0
    python ml/evaluate.py --api https://your-app.onrender.com --sleep 7   # free Gemini tier

The pipeline skips its cache when source=test, so every message gets a full check.
"""
from __future__ import annotations

import argparse
import csv
import json
import statistics
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
TEST_CSV = ROOT / "ml" / "data" / "test_set.csv"
OUT_MD = ROOT / "docs" / "evaluation.md"


def run(api: str, sleep: float, limit: int | None) -> dict:
    rows = list(csv.DictReader(TEST_CSV.open(encoding="utf-8")))
    if limit:
        rows = rows[:limit]
    tp = fp = fn = tn = 0
    scam_called_scam = 0
    times: list[float] = []
    misses: list[dict] = []

    with httpx.Client(timeout=60) as client:
        for index, row in enumerate(rows, 1):
            started = time.time()
            try:
                response = client.post(
                    f"{api.rstrip('/')}/api/analyze",
                    data={"kind": "text", "content": row["text"], "lang": "en",
                          "source": "test", "want_audio": "false"},
                )
                result = response.json()
            except Exception as exc:
                print(f"  request {index} failed: {exc}")
                continue
            times.append(time.time() - started)

            is_scam = row["label"] == "1"
            flagged = result.get("verdict") != "SAFE"
            if is_scam and flagged:
                tp += 1
                scam_called_scam += result.get("verdict") == "SCAM"
            elif is_scam and not flagged:
                fn += 1
                misses.append({"text": row["text"][:120], "verdict": result.get("verdict"),
                               "risk": result.get("risk"), "expected": "scam"})
            elif not is_scam and flagged:
                fp += 1
                misses.append({"text": row["text"][:120], "verdict": result.get("verdict"),
                               "risk": result.get("risk"), "expected": "genuine"})
            else:
                tn += 1

            if index % 25 == 0:
                print(f"  {index}/{len(rows)} checked")
            if sleep:
                time.sleep(sleep)

    total = tp + fp + fn + tn
    metrics = {
        "messages": total,
        "scams": tp + fn,
        "genuine": tn + fp,
        "detection_rate": round(100 * tp / (tp + fn), 1) if (tp + fn) else 0.0,
        "called_scam_outright": round(100 * scam_called_scam / (tp + fn), 1) if (tp + fn) else 0.0,
        "false_alarm_rate": round(100 * fp / (fp + tn), 1) if (fp + tn) else 0.0,
        "precision": round(100 * tp / (tp + fp), 1) if (tp + fp) else 0.0,
        "accuracy": round(100 * (tp + tn) / total, 1) if total else 0.0,
        "median_seconds": round(statistics.median(times), 2) if times else 0.0,
        "slowest_seconds": round(max(times), 2) if times else 0.0,
        "confusion": {"tp": tp, "fp": fp, "fn": fn, "tn": tn},
        "misses": misses[:15],
    }
    return metrics


def write_markdown(metrics: dict, api: str, engine: str) -> None:
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    rows = [
        ("Messages tested", metrics["messages"]),
        ("Scam messages caught (scam or suspicious)", f"{metrics['detection_rate']}%"),
        ("Scam messages called Scam outright", f"{metrics['called_scam_outright']}%"),
        ("Genuine messages wrongly flagged", f"{metrics['false_alarm_rate']}%"),
        ("Precision on flagged messages", f"{metrics['precision']}%"),
        ("Overall accuracy", f"{metrics['accuracy']}%"),
        ("Median time per check", f"{metrics['median_seconds']} s"),
        ("Slowest check", f"{metrics['slowest_seconds']} s"),
    ]
    lines = [
        "# Evaluation",
        "",
        f"Run against `{api}` with the engine reported as **{engine}**, on "
        f"{metrics['messages']} held-out messages "
        f"({metrics['scams']} scam, {metrics['genuine']} genuine) whose wording never appears "
        "in training data or in the prompt.",
        "",
        "| Measure | Result |",
        "| --- | --- |",
    ]
    lines += [f"| {name} | {value} |" for name, value in rows]
    confusion = metrics["confusion"]
    lines += [
        "",
        "Confusion matrix: "
        f"true positives {confusion['tp']}, false negatives {confusion['fn']}, "
        f"false positives {confusion['fp']}, true negatives {confusion['tn']}.",
        "",
    ]
    lines += [
        "## What this number does not prove",
        "",
        "The seed test set is made of message templates the team wrote from public scam advisories,",
        "news reports and messages on our own phones. It measures whether the system generalises to",
        "wording it has never seen, but it is still our own writing, so real inboxes will be harder.",
        "Replace `ml/data/test_set.csv` with real forwarded messages as the pilot collects them and",
        "run this script again before quoting a number anywhere.",
        "",
    ]
    if metrics["misses"]:
        lines += ["## Where it was wrong", "", "| Message | Verdict | Risk | Should have been |",
                  "| --- | --- | --- | --- |"]
        for miss in metrics["misses"]:
            text = miss["text"].replace("|", " ")
            lines.append(f"| {text} | {miss['verdict']} | {miss['risk']} | {miss['expected']} |")
        lines.append("")
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {OUT_MD.relative_to(ROOT)}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", default="http://localhost:8000")
    parser.add_argument("--sleep", type=float, default=0.0,
                        help="seconds between requests, use 7 on the Gemini free tier")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    engine = "unknown"
    try:
        engine = httpx.get(f"{args.api.rstrip('/')}/api/meta", timeout=10).json().get("engine", "unknown")
    except Exception:
        pass

    print(f"evaluating {args.api} (engine: {engine})")
    metrics = run(args.api, args.sleep, args.limit)
    print(json.dumps({k: v for k, v in metrics.items() if k != "misses"}, indent=2))
    write_markdown(metrics, args.api, engine)


if __name__ == "__main__":
    main()
