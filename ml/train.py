"""Train the scam classifier and save it where the backend expects it.

    python ml/generate_seed.py && python ml/train.py
"""
from __future__ import annotations

import json
from pathlib import Path

import joblib
import pandas as pd
import sklearn
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline, make_union

ROOT = Path(__file__).resolve().parents[1]
TRAIN_CSV = ROOT / "ml" / "data" / "train.csv"
MODEL_PATH = ROOT / "backend" / "models" / "scam_clf.joblib"
METRICS_PATH = ROOT / "ml" / "data" / "model_metrics.json"


def build_model():
    return make_pipeline(
        make_union(
            TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True),
            TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=2, sublinear_tf=True),
        ),
        LogisticRegression(max_iter=2000, class_weight="balanced"),
    )


def main() -> None:
    frame = pd.read_csv(TRAIN_CSV)
    frame = frame.dropna(subset=["text", "label"])
    frame["label"] = frame["label"].astype(int)

    x_train, x_dev, y_train, y_dev = train_test_split(
        frame["text"], frame["label"], test_size=0.2, stratify=frame["label"], random_state=42)

    model = build_model()
    model.fit(x_train, y_train)
    predictions = model.predict(x_dev)

    report = classification_report(y_dev, predictions, digits=3,
                                   target_names=["genuine", "scam"], output_dict=True)
    print(classification_report(y_dev, predictions, digits=3, target_names=["genuine", "scam"]))
    print("confusion matrix [[TN FP] [FN TP]]:")
    print(confusion_matrix(y_dev, predictions))

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    METRICS_PATH.write_text(json.dumps({
        "rows": int(len(frame)),
        "held_out_rows": int(len(x_dev)),
        "sklearn_version": sklearn.__version__,
        "report": report,
    }, indent=2), encoding="utf-8")

    size_kb = MODEL_PATH.stat().st_size / 1024
    print("\nNote: this split shares templates with training, so it always looks near perfect.")
    print("The honest number is ml/evaluate.py on the held-out templates in test_set.csv.")
    print(f"\nsaved {MODEL_PATH.relative_to(ROOT)} ({size_kb:.0f} KB), scikit-learn {sklearn.__version__}")
    print("pin this scikit-learn version in backend/requirements.txt")


if __name__ == "__main__":
    main()
