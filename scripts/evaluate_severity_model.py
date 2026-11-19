import sys
import os
import json
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score, precision_recall_fscore_support

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.ai.severity.dataset import generate_synthetic_severity_dataset
from app.ai.severity.model import load_trained_severity_model, CLASSES

def evaluate_model():
    print("===============================================================")
    print(" DIRS PHASE 3A — INCIDENT SEVERITY MODEL EVALUATION REPORT")
    print(" NOTE: Development Model Trained on Synthetic Disaster Dataset")
    print("===============================================================\n")

    X, y, _ = generate_synthetic_severity_dataset(n_samples_per_class=500, random_seed=99)
    _, X_test, _, y_test = train_test_split(X, y, test_size=0.30, random_state=99, stratify=y)

    model = load_trained_severity_model()
    y_pred = model.predict(X_test)

    acc = accuracy_score(y_test, y_pred)
    prec_macro, rec_macro, f1_macro, _ = precision_recall_fscore_support(y_test, y_pred, average='macro')

    cm = confusion_matrix(y_test, y_pred, labels=CLASSES)
    report_dict = classification_report(y_test, y_pred, labels=CLASSES, output_dict=True)
    report_text = classification_report(y_test, y_pred, labels=CLASSES)

    print(f"Overall Model Accuracy: {acc * 100:.2f}%")
    print(f"Macro Precision:       {prec_macro * 100:.2f}%")
    print(f"Macro Recall:          {rec_macro * 100:.2f}%")
    print(f"Macro F1 Score:        {f1_macro * 100:.2f}%")
    print("\n--- Detailed Classification Report ---")
    print(report_text)

    print("--- Confusion Matrix ---")
    print(f"Labels Order: {CLASSES}")
    print(cm)

    print("\n--- Special Attention: Safety Critical Recalls ---")
    critical_recall = report_dict.get('CRITICAL', {}).get('recall', 0.0)
    high_recall = report_dict.get('HIGH', {}).get('recall', 0.0)
    print(f"CRITICAL Recall: {critical_recall * 100:.2f}%")
    print(f"HIGH Recall:     {high_recall * 100:.2f}%")

    eval_summary = {
        "dataset_type": "Development Synthetic Dataset (Not Real-World Validation)",
        "samples_evaluated": len(y_test),
        "overall_accuracy": round(float(acc), 4),
        "macro_f1": round(float(f1_macro), 4),
        "critical_recall": round(float(critical_recall), 4),
        "high_recall": round(float(high_recall), 4),
        "confusion_matrix": cm.tolist()
    }

    docs_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "docs"))
    os.makedirs(docs_dir, exist_ok=True)
    eval_file = os.path.join(docs_dir, "PHASE3A_EVALUATION.md")

    with open(eval_file, "w") as f:
        f.write("# DIRS Phase 3A — Model Evaluation Report\n\n")
        f.write("> **Dataset Notice:** Development Model Trained Using Synthetic Data (1,500 samples). Not Real-World Field Validation.\n\n")
        f.write("## Performance Metrics Summary\n\n")
        f.write(f"- **Overall Accuracy:** {acc * 100:.2f}%\n")
        f.write(f"- **Macro Precision:** {prec_macro * 100:.2f}%\n")
        f.write(f"- **Macro Recall:** {rec_macro * 100:.2f}%\n")
        f.write(f"- **Macro F1 Score:** {f1_macro * 100:.2f}%\n")
        f.write(f"- **CRITICAL Class Recall:** {critical_recall * 100:.2f}%\n")
        f.write(f"- **HIGH Class Recall:** {high_recall * 100:.2f}%\n\n")
        f.write("## Per-Class Classification Metrics\n\n```text\n")
        f.write(report_text)
        f.write("\n```\n\n## Confusion Matrix\n\n```text\n")
        f.write(f"Labels Order: {CLASSES}\n")
        f.write(str(cm))
        f.write("\n```\n")

    print(f"\nEvaluation summary saved to: {eval_file}")

if __name__ == "__main__":
    evaluate_model()
