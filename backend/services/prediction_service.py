import os
import re

import joblib
import numpy as np

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MODEL_DIR = os.path.join(BASE_DIR, "ml", "models")

LEVEL_NAMES = {0: "Low", 1: "Medium", 2: "High"}

FILLER = r"\b(ngl|tbh|lowkey|honestly|not gonna lie|just saying|so yeah|that's all|" \
         r"i dunno|idk|um|uh|okay so|listen|dude|yeah|whatever|sigh|ugh)\b"

CONTRACTIONS = {
    "can't": "cannot", "won't": "will not", "n't": " not", "'m": " am",
    "'re": " are", "'ve": " have", "'ll": " will", "'d": " would", "'s": " is",
}

CRISIS_PATTERNS = [
    r"\bkill myself\b", r"\bend my life\b", r"\bsuicid", r"\bself[- ]harm\b",
    r"\bhurt myself\b", r"\bno reason to live\b", r"\bwant to die\b",
    r"\bbetter off dead\b", r"\bcut myself\b",
]

THEME_ADVICE = {
    "academics": "Speak to your faculty advisor about workload or deadline extensions.",
    "burnout": "Schedule genuine recovery time - rest is not the same as scrolling.",
    "family": "Set gentle boundaries; a counsellor can help you script difficult conversations.",
    "finance": "The student welfare office handles fee deferrals and hardship grants.",
    "future_worry": "Career services run one-to-one planning sessions that reduce uncertainty.",
    "health": "Book a campus clinic appointment; physical and mental health track together.",
    "loneliness": "Join one recurring group activity - repetition builds connection faster than one-offs.",
    "relationships": "Individual counselling helps even when the difficulty involves someone else.",
    "self_esteem": "CBT-based self-worth modules are available in the resource library.",
    "sleep": "Fix a wake-up time first; the sleep time follows. Avoid screens for an hour before bed.",
    "social_anxiety": "Graded exposure with a counsellor is highly effective for social anxiety.",
    "time_management": "Timetable your work in blocks and protect one evening a week as free.",
    "work": "Discuss workload with your supervisor or the internship coordinator.",
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


class StressPredictor:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._loaded = False
        return cls._instance

    def __init__(self):
        if self._loaded:
            return
        required = ["vectorizer.pkl", "stress_model.pkl",
                    "theme_vectorizer.pkl", "theme_model.pkl"]
        missing = [f for f in required
                   if not os.path.exists(os.path.join(MODEL_DIR, f))]
        if missing:
            raise FileNotFoundError(
                f"Missing model artefacts {missing}. Run: python ml/train_model.py")
        self.vectorizer = joblib.load(os.path.join(MODEL_DIR, "vectorizer.pkl"))
        self.model = joblib.load(os.path.join(MODEL_DIR, "stress_model.pkl"))
        self.theme_vectorizer = joblib.load(os.path.join(MODEL_DIR, "theme_vectorizer.pkl"))
        self.theme_model = joblib.load(os.path.join(MODEL_DIR, "theme_model.pkl"))
        self.feature_names = np.array(self.vectorizer.get_feature_names_out())
        self._loaded = True

    def _top_features(self, vec, level, k=6):
        if not hasattr(self.model, "coef_"):
            return []
        idx = vec.nonzero()[1]
        if len(idx) == 0:
            return []
        coefs = self.model.coef_[level][idx]
        order = np.argsort(coefs)[::-1][:k]
        return [(self.feature_names[idx[i]], round(float(coefs[i]), 4))
                for i in order if coefs[i] > 0]

    @staticmethod
    def detect_crisis(text: str):
        low = str(text).lower()
        return [p for p in CRISIS_PATTERNS if re.search(p, low)]

    def predict(self, text: str) -> dict:
        cleaned = clean_text(text)
        if not cleaned:
            raise ValueError("Text contains no analysable content.")

        vec = self.vectorizer.transform([cleaned])
        proba = self.model.predict_proba(vec)[0]
        level = int(np.argmax(proba))
        confidence = float(proba[level])

        theme_code = str(self.theme_model.predict(
            self.theme_vectorizer.transform([cleaned]))[0])
        theme_proba = self.theme_model.predict_proba(
            self.theme_vectorizer.transform([cleaned]))[0]

        crisis = self.detect_crisis(text)
        if crisis:
            level, confidence = 2, max(confidence, 0.99)

        return {
            "level": level,
            "level_name": LEVEL_NAMES[level],
            "confidence": round(confidence, 4),
            "probabilities": [round(float(p), 4) for p in proba],
            "theme_code": theme_code,
            "theme_confidence": round(float(np.max(theme_proba)), 4),
            "keywords": cleaned.split(),
            "top_features": self._top_features(vec, level),
            "crisis_flagged": bool(crisis),
            "cleaned_text": cleaned,
        }
