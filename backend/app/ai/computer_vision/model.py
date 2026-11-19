import os
import joblib
import numpy as np
from typing import Dict, Any
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, classification_report, confusion_matrix
from app.ai.computer_vision.dataset import generate_synthetic_cv_dataset
from app.ai.computer_vision.features import DAMAGE_CLASSES

MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "models")
CV_MODEL_PATH = os.path.join(MODEL_DIR, "cv_damage_model.pkl")

def train_and_evaluate_cv_model() -> Dict[str, Any]:
    """
    Trains LogisticRegression and RandomForestClassifier on synthetic CV image feature dataset.
    Evaluates both models and persists the best model to cv_damage_model.pkl.
    """
    X, y, _ = generate_synthetic_cv_dataset(n_samples_per_class=200, random_seed=42)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=42, stratify=y)

    # 1. Logistic Regression Baseline
    lr = LogisticRegression(max_iter=1000, random_state=42)
    lr.fit(X_train, y_train)
    y_pred_lr = lr.predict(X_test)
    acc_lr = accuracy_score(y_test, y_pred_lr)
    prec_lr, rec_lr, f1_lr, _ = precision_recall_fscore_support(y_test, y_pred_lr, average='macro')

    # 2. Random Forest Candidate Model
    rf = RandomForestClassifier(n_estimators=100, max_depth=8, random_state=42)
    rf.fit(X_train, y_train)
    y_pred_rf = rf.predict(X_test)
    acc_rf = accuracy_score(y_test, y_pred_rf)
    prec_rf, rec_rf, f1_rf, _ = precision_recall_fscore_support(y_test, y_pred_rf, average='macro')
    report_rf = classification_report(y_test, y_pred_rf, labels=DAMAGE_CLASSES, output_dict=True)

    cm_rf = confusion_matrix(y_test, y_pred_rf, labels=DAMAGE_CLASSES)

    os.makedirs(MODEL_DIR, exist_ok=True)
    best_model = rf if f1_rf >= f1_lr else lr
    joblib.dump(best_model, CV_MODEL_PATH)

    results = {
        "selected_model": "RandomForestClassifier" if best_model == rf else "LogisticRegression",
        "logistic_regression": {
            "accuracy": round(float(acc_lr), 4),
            "precision_macro": round(float(prec_lr), 4),
            "recall_macro": round(float(rec_lr), 4),
            "f1_macro": round(float(f1_lr), 4)
        },
        "random_forest": {
            "accuracy": round(float(acc_rf), 4),
            "precision_macro": round(float(prec_rf), 4),
            "recall_macro": round(float(rec_rf), 4),
            "f1_macro": round(float(f1_rf), 4),
            "severe_recall": round(float(report_rf.get('SEVERE_DAMAGE', {}).get('recall', 0.0)), 4),
            "destroyed_recall": round(float(report_rf.get('DESTROYED', {}).get('recall', 0.0)), 4),
            "confusion_matrix": cm_rf.tolist()
        }
    }
    return results

def load_trained_cv_model() -> Any:
    """
    Loads persisted CV damage classifier from disk. Trains on demand if missing.
    """
    if not os.path.exists(CV_MODEL_PATH):
        train_and_evaluate_cv_model()
    return joblib.load(CV_MODEL_PATH)
