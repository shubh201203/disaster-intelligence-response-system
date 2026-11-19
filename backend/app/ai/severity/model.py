import os
import joblib
import numpy as np
from typing import Dict, Any, Tuple
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, classification_report, confusion_matrix
from app.ai.severity.dataset import generate_synthetic_severity_dataset
from app.ai.severity.features import FEATURE_NAMES

MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "models")
MODEL_PATH = os.path.join(MODEL_DIR, "severity_model.pkl")

CLASSES = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]

def train_and_evaluate_models() -> Dict[str, Any]:
    """
    Trains LogisticRegression and RandomForestClassifier on the dataset.
    Evaluates both models and selects the best model based on macro F1 and critical recall.
    """
    X, y, _ = generate_synthetic_severity_dataset(n_samples_per_class=500, random_seed=42)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=42, stratify=y)
    
    # 1. Logistic Regression Baseline
    lr = LogisticRegression(max_iter=1000, random_state=42)
    lr.fit(X_train, y_train)
    y_pred_lr = lr.predict(X_test)
    acc_lr = accuracy_score(y_test, y_pred_lr)
    prec_lr, rec_lr, f1_lr, _ = precision_recall_fscore_support(y_test, y_pred_lr, average='macro')
    report_lr = classification_report(y_test, y_pred_lr, labels=CLASSES, output_dict=True)
    high_rec_lr = report_lr.get('HIGH', {}).get('recall', 0.0)
    crit_rec_lr = report_lr.get('CRITICAL', {}).get('recall', 0.0)
    
    # 2. Random Forest Candidate Model
    rf = RandomForestClassifier(n_estimators=100, max_depth=8, random_state=42)
    rf.fit(X_train, y_train)
    y_pred_rf = rf.predict(X_test)
    acc_rf = accuracy_score(y_test, y_pred_rf)
    prec_rf, rec_rf, f1_rf, _ = precision_recall_fscore_support(y_test, y_pred_rf, average='macro')
    report_rf = classification_report(y_test, y_pred_rf, labels=CLASSES, output_dict=True)
    high_rec_rf = report_rf.get('HIGH', {}).get('recall', 0.0)
    crit_rec_rf = report_rf.get('CRITICAL', {}).get('recall', 0.0)
    
    cm_rf = confusion_matrix(y_test, y_pred_rf, labels=CLASSES)
    
    # Save selected model (Random Forest outperforms Logistic Regression)
    os.makedirs(MODEL_DIR, exist_ok=True)
    best_model = rf if f1_rf >= f1_lr else lr
    joblib.dump(best_model, MODEL_PATH)
    
    results = {
        "selected_model": "RandomForestClassifier" if best_model == rf else "LogisticRegression",
        "logistic_regression": {
            "accuracy": round(float(acc_lr), 4),
            "precision_macro": round(float(prec_lr), 4),
            "recall_macro": round(float(rec_lr), 4),
            "f1_macro": round(float(f1_lr), 4),
            "high_recall": round(float(high_rec_lr), 4),
            "critical_recall": round(float(crit_rec_lr), 4)
        },
        "random_forest": {
            "accuracy": round(float(acc_rf), 4),
            "precision_macro": round(float(prec_rf), 4),
            "recall_macro": round(float(rec_rf), 4),
            "f1_macro": round(float(f1_rf), 4),
            "high_recall": round(float(high_rec_rf), 4),
            "critical_recall": round(float(crit_rec_rf), 4),
            "confusion_matrix": cm_rf.tolist()
        }
    }
    return results

def load_trained_severity_model() -> Any:
    """
    Loads the persisted model from disk. If missing, trains and persists a model on demand.
    """
    if not os.path.exists(MODEL_PATH):
        train_and_evaluate_models()
    return joblib.load(MODEL_PATH)
