"""Trains the intent classifier on data/training_data.json and saves it to models/intent_pipeline.joblib."""

import json
from pathlib import Path

import joblib
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "data" / "training_data.json"
MODEL_PATH = ROOT / "models" / "intent_pipeline.joblib"


def load_training_data():
    with open(DATA_PATH, encoding="utf-8") as f:
        rows = json.load(f)
    texts = [row["text"] for row in rows]
    intents = [row["intent"] for row in rows]
    return texts, intents


def train():
    texts, intents = load_training_data()

    X_train, X_test, y_train, y_test = train_test_split(
        texts, intents, test_size=0.2, random_state=42, stratify=intents
    )

    # C=5 sharpens predict_proba enough that short, clear-cut queries (e.g. "hi",
    # "block my debit card") cross the confidence threshold, while gibberish
    # input still stays low-confidence and correctly falls back.
    pipeline = Pipeline([
        ("tfidf", TfidfVectorizer(ngram_range=(1, 2))),
        ("clf", LogisticRegression(max_iter=1000, C=5)),
    ])

    pipeline.fit(X_train, y_train)

    y_pred = pipeline.predict(X_test)
    print("Holdout accuracy:", pipeline.score(X_test, y_test))
    print(classification_report(y_test, y_pred, zero_division=0))

    # The holdout split above is only for reporting a trustworthy accuracy
    # number. The model we actually ship is refit on the full dataset so no
    # training examples are wasted on evaluation at inference time.
    pipeline.fit(texts, intents)

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, MODEL_PATH)
    print(f"Saved model to {MODEL_PATH}")


if __name__ == "__main__":
    train()
