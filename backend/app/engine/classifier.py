"""Scam classifier: TF-IDF word and character n-grams plus logistic regression.

Small, fast and explainable. If the model file is missing the app still works;
the score simply drops out of the evidence.
"""
from __future__ import annotations

from pathlib import Path

MODEL_PATH = Path(__file__).resolve().parents[2] / "models" / "scam_clf.joblib"

_model = None
_loaded = False


def _load():
    global _model, _loaded
    if _loaded:
        return _model
    _loaded = True
    try:
        import joblib
        if MODEL_PATH.exists():
            _model = joblib.load(MODEL_PATH)
    except Exception:
        _model = None
    return _model


def available() -> bool:
    return _load() is not None


def score(text: str) -> float | None:
    """Probability that the message is a scam, or None when no model is loaded."""
    model = _load()
    if model is None or not (text or "").strip():
        return None
    try:
        return float(model.predict_proba([text])[0][1])
    except Exception:
        return None


def top_words(text: str, n: int = 4) -> list[str]:
    """Words that pushed the score up. Used for the 'why' when Gemini is off."""
    model = _load()
    if model is None:
        return []
    try:
        union = model.named_steps["featureunion"]
        clf = model.named_steps["logisticregression"]
        word_vec = union.transformer_list[0][1]
        names = word_vec.get_feature_names_out()
        weights = clf.coef_[0][: len(names)]
        row = word_vec.transform([text])
        pairs = [(names[i], weights[i] * row[0, i]) for i in row.nonzero()[1]]
        pairs.sort(key=lambda p: -p[1])
        return [w for w, score_ in pairs[:n] if score_ > 0]
    except Exception:
        return []
