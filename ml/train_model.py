import json
import os
import re
import sys
import time
import warnings

warnings.filterwarnings("ignore")

import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, classification_report,
                             confusion_matrix, f1_score, precision_score,
                             recall_score)
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import MultinomialNB
from sklearn.svm import LinearSVC

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_CSV = os.path.join(BASE_DIR, "data", "synthetic_stress_dataset.csv")
MODEL_DIR = os.path.join(BASE_DIR, "ml", "models")
RANDOM_STATE = 42

LEVEL_NAMES = {0: "Low", 1: "Medium", 2: "High"}

FILLER = r"\b(ngl|tbh|lowkey|honestly|not gonna lie|just saying|so yeah|that's all|" \
         r"i dunno|idk|um|uh|okay so|listen|dude|yeah|whatever|sigh|ugh)\b"

CONTRACTIONS = {
    "can't": "cannot", "won't": "will not", "n't": " not", "'m": " am",
    "'re": " are", "'ve": " have", "'ll": " will", "'d": " would", "'s": " is",
}


def clean_text(text: str) -> str:
    t = str(text).lower()
    t = re.sub(r"http\S+|www\.\S+", " ", t)
    t = re.sub(r"\S+@\S+", " ", t)
    for src, dst in CONTRACTIONS.items():
        t = t.replace(src, dst)
    t = re.sub(FILLER, " ", t)
    t = re.sub(r"[^a-z\s]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def build_candidates():
    return {
        "Logistic Regression": LogisticRegression(
            max_iter=1000, C=4.0, random_state=RANDOM_STATE),
        "Multinomial Naive Bayes": MultinomialNB(alpha=0.3),
        "Linear SVM": CalibratedClassifierCV(
            LinearSVC(C=0.5, random_state=RANDOM_STATE), cv=3),
        "Random Forest": RandomForestClassifier(
            n_estimators=300, min_samples_leaf=2,
            random_state=RANDOM_STATE, n_jobs=-1),
    }


def main():
    if not os.path.exists(DATA_CSV):
        sys.exit(f"Dataset not found at {DATA_CSV}")
    os.makedirs(MODEL_DIR, exist_ok=True)

    print("=" * 74)
    print("  MindCare  -  Stress Level Classifier Training")
    print("=" * 74)

    df = pd.read_csv(DATA_CSV)
    df["clean"] = df["text"].apply(clean_text)
    df = df[df["clean"].str.len() > 0].reset_index(drop=True)

    print(f"\n[1] Dataset loaded          : {len(df)} rows")
    print(f"    Class balance           : "
          f"{ {LEVEL_NAMES[k]: int(v) for k, v in df['label'].value_counts().sort_index().items()} }")
    print(f"    Distinct themes         : {df['theme'].nunique()}")

    X_train, X_test, y_train, y_test = train_test_split(
        df["clean"], df["label"], test_size=0.20,
        stratify=df["label"], random_state=RANDOM_STATE)
    print(f"\n[2] Stratified 80:20 split  : {len(X_train)} train / {len(X_test)} test")

    vectorizer = TfidfVectorizer(
        ngram_range=(1, 2), min_df=2, max_df=0.9,
        sublinear_tf=True, max_features=8000)
    Xtr = vectorizer.fit_transform(X_train)
    Xte = vectorizer.transform(X_test)
    print(f"[3] TF-IDF feature space    : {Xtr.shape[1]} features (1-2 grams)")

    print(f"\n[4] Training and comparing {len(build_candidates())} models\n")
    print(f"    {'Model':<26}{'Accuracy':>10}{'Macro F1':>10}"
          f"{'Precision':>11}{'Recall':>9}{'Time':>8}")
    print("    " + "-" * 66)

    results = {}
    for name, clf in build_candidates().items():
        t0 = time.time()
        clf.fit(Xtr, y_train)
        pred = clf.predict(Xte)
        elapsed = time.time() - t0
        results[name] = {
            "model": clf,
            "accuracy": accuracy_score(y_test, pred),
            "f1_macro": f1_score(y_test, pred, average="macro"),
            "precision_macro": precision_score(y_test, pred, average="macro", zero_division=0),
            "recall_macro": recall_score(y_test, pred, average="macro"),
            "train_seconds": elapsed,
            "predictions": pred,
        }
        r = results[name]
        print(f"    {name:<26}{r['accuracy']:>9.4f}{r['f1_macro']:>10.4f}"
              f"{r['precision_macro']:>11.4f}{r['recall_macro']:>9.4f}{elapsed:>7.1f}s")

    best_name = max(results, key=lambda k: results[k]["f1_macro"])
    best = results[best_name]
    print(f"\n[5] Best model              : {best_name} "
          f"(macro F1 = {best['f1_macro']:.4f})")

    print("\n[6] Per-class report for the winning model\n")
    print(classification_report(
        y_test, best["predictions"],
        target_names=[LEVEL_NAMES[i] for i in sorted(LEVEL_NAMES)], digits=4))

    cm = confusion_matrix(y_test, best["predictions"])
    print("    Confusion matrix (rows = actual, cols = predicted)")
    print(f"    {'':<12}" + "".join(f"{LEVEL_NAMES[i]:>11}" for i in range(3)))
    for i, row in enumerate(cm):
        print(f"    {LEVEL_NAMES[i]:<12}" + "".join(f"{v:>11}" for v in row))

    print("\n[7] Training auxiliary theme classifier (13 classes)")
    tX_train, tX_test, ty_train, ty_test = train_test_split(
        df["clean"], df["theme"], test_size=0.20,
        stratify=df["theme"], random_state=RANDOM_STATE)
    theme_vec = TfidfVectorizer(ngram_range=(1, 2), min_df=2,
                                sublinear_tf=True, max_features=8000)
    theme_clf = LogisticRegression(max_iter=1000, C=4.0, random_state=RANDOM_STATE)
    theme_clf.fit(theme_vec.fit_transform(tX_train), ty_train)
    theme_acc = accuracy_score(ty_test, theme_clf.predict(theme_vec.transform(tX_test)))
    print(f"    Theme accuracy          : {theme_acc:.4f}")

    joblib.dump(vectorizer, os.path.join(MODEL_DIR, "vectorizer.pkl"))
    joblib.dump(best["model"], os.path.join(MODEL_DIR, "stress_model.pkl"))
    joblib.dump(theme_vec, os.path.join(MODEL_DIR, "theme_vectorizer.pkl"))
    joblib.dump(theme_clf, os.path.join(MODEL_DIR, "theme_model.pkl"))

    metadata = {
        "model_name": "MindCare Stress Classifier",
        "algorithm": best_name,
        "version": "1.0",
        "accuracy": round(best["accuracy"], 6),
        "precision_macro": round(best["precision_macro"], 6),
        "recall_macro": round(best["recall_macro"], 6),
        "f1_macro": round(best["f1_macro"], 6),
        "train_size": int(len(X_train)),
        "test_size": int(len(X_test)),
        "feature_count": int(Xtr.shape[1]),
        "theme_accuracy": round(theme_acc, 6),
        "confusion_matrix": cm.tolist(),
        "comparison": {
            n: {k: round(v, 6) for k, v in r.items()
                if k in ("accuracy", "f1_macro", "precision_macro",
                         "recall_macro", "train_seconds")}
            for n, r in results.items()
        },
    }
    with open(os.path.join(MODEL_DIR, "metadata.json"), "w") as fh:
        json.dump(metadata, fh, indent=2)

    print(f"\n[8] Artefacts saved to      : ml/models/")
    print("    vectorizer.pkl, stress_model.pkl, theme_vectorizer.pkl,")
    print("    theme_model.pkl, metadata.json")
    print("\nTraining complete.\n")


if __name__ == "__main__":
    main()
