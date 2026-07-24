"""Loads the trained intent pipeline and exposes a simple predict() function."""

from pathlib import Path

import joblib

ROOT = Path(__file__).resolve().parent.parent
MODEL_PATH = ROOT / "models" / "intent_pipeline.joblib"

CONFIDENCE_THRESHOLD = 0.4

_pipeline = None


def _get_pipeline():
    global _pipeline
    if _pipeline is None:
        if not MODEL_PATH.exists():
            raise FileNotFoundError(
                f"No trained model found at {MODEL_PATH}. Run `python chatbot/train.py` first."
            )
        _pipeline = joblib.load(MODEL_PATH)
    return _pipeline


def predict(text):
    """Returns (intent, confidence). intent is 'fallback' if confidence is below threshold."""
    pipeline = _get_pipeline()
    probabilities = pipeline.predict_proba([text])[0]
    classes = pipeline.classes_

    best_index = probabilities.argmax()
    confidence = float(probabilities[best_index])
    intent = classes[best_index]

    if confidence < CONFIDENCE_THRESHOLD:
        return "fallback", confidence

    return intent, confidence
