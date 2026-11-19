# DIRS Phase 3A — Model Evaluation Report

> **Dataset Notice:** Development Model Trained Using Synthetic Data (1,500 samples). Not Real-World Field Validation.

## Performance Metrics Summary

- **Overall Accuracy:** 100.00%
- **Macro Precision:** 100.00%
- **Macro Recall:** 100.00%
- **Macro F1 Score:** 100.00%
- **CRITICAL Class Recall:** 100.00%
- **HIGH Class Recall:** 100.00%

## Per-Class Classification Metrics

```text
              precision    recall  f1-score   support

         LOW       1.00      1.00      1.00       150
      MEDIUM       1.00      1.00      1.00       150
        HIGH       1.00      1.00      1.00       150
    CRITICAL       1.00      1.00      1.00       150

    accuracy                           1.00       600
   macro avg       1.00      1.00      1.00       600
weighted avg       1.00      1.00      1.00       600

```

## Confusion Matrix

```text
Labels Order: ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']
[[150   0   0   0]
 [  0 150   0   0]
 [  0   0 150   0]
 [  0   0   0 150]]
```
