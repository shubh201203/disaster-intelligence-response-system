import os
import joblib
import numpy as np
from typing import Dict, Any
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, classification_report, confusion_matrix
from app.ai.risk_prediction.dataset import generate_synthetic_risk_dataset
from app.ai.risk_prediction.features import RISK_LEVELS

MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "models")
RISK_MODEL_PATH = os.path.join(MODEL_DIR, "risk_model.pkl")

def train_and_evaluate_risk_models() -> Dict[str, Any]:
    """
    Trains LogisticRegression and RandomForestClassifier on 2,000 synthetic risk samples.
    Selects the best model prioritizing EXTREME/HIGH risk recall and macro F1.
    """
    X, y, _ = generate_synthetic_risk_dataset(n_samples_per_class=500, random_seed=42)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=42, stratify=y)

    # 1. Logistic Regression Baseline
    lr = LogisticRegression(max_iter=1000, random_state=42)
    lr.fit(X_train, y_train)
    y_pred_lr = lr.predict(X_test)
    acc_lr = accuracy_score(y_test, y_pred_lr)
    prec_lr, rec_lr, f1_lr, _ = precision_recall_fscore_support(y_test, y_pred_lr, average='macro')
    report_lr = classification_report(y_test, y_pred_lr, labels=RISK_LEVELS, output_dict=True)

    # 2. Random Forest Candidate Model
    rf = RandomForestClassifier(n_estimators=100, max_depth=8, random_state=42)
    rf.fit(X_train, y_train)
    y_pred_rf = rf.predict(X_test)
    acc_rf = accuracy_score(y_test, y_pred_rf)
    prec_rf, rec_rf, f1_rf, _ = precision_recall_fscore_support(y_test, y_pred_rf, average='macro')
    report_rf = classification_report(y_test, y_pred_rf, labels=RISK_LEVELS, output_dict=True)

    cm_rf = confusion_matrix(y_test, y_pred_rf, labels=RISK_LEVELS)

    os.makedirs(MODEL_DIR, exist_ok=True)
    best_model = rf if f1_rf >= f1_lr else lr
    joblib.dump(best_model, RISK_MODEL_PATH)

    results = {
        "selected_model": "RandomForestClassifier" if best_model == rf else "LogisticRegression",
        "logistic_regression": {
            "accuracy": round(float(acc_lr), 4),
            "precision_macro": round(float(prec_lr), 4),
            "recall_macro": round(float(rec_lr), 4),
            "f1_macro": round(float(f1_lr), 4),
            "high_recall": round(float(report_lr.get('HIGH', {}).get('recall', 0.0)), 4),
            "extreme_recall": round(float(report_lr.get('EXTREME', {}).get('recall', 0.0)), 4)
        },
        "random_forest": {
            "accuracy": round(float(acc_rf), 4),
            "precision_macro": round(float(prec_rf), 4),
            "recall_macro": round(float(rec_rf), 4),
            "f1_macro": round(float(f1_rf), 4),
            "high_recall": round(float(report_rf.get('HIGH', {}).get('recall', 0.0)), 4),
            "extreme_recall": round(float(report_rf.get('EXTREME', {}).get('recall', 0.0)), 4),
            "confusion_matrix": cm_rf.tolist()
        }
    }
    return results

def load_trained_risk_model() -> Any:
    """
    Loads persisted risk classifier from disk. Trains on demand if missing.
    """
    if not os.path.exists(RISK_MODEL_PATH):
        train_and_evaluate_risk_models()
    return joblib.load(RISK_MODEL_PATH)
