class ConfidenceEvaluator:
    # Configurable confidence threshold for triggering human review
    CONFIDENCE_THRESHOLD: float = 70.0

    @classmethod
    def evaluate(cls, confidence_score: float) -> bool:
        """
        Returns True if human review is required (confidence < threshold).
        """
        return confidence_score < cls.CONFIDENCE_THRESHOLD

    @classmethod
    def format_confidence_label(cls, confidence_score: float) -> str:
        if confidence_score >= 85.0:
            return "HIGH CONFIDENCE"
        elif confidence_score >= 70.0:
            return "MODERATE CONFIDENCE"
        else:
            return "REQUIRES HUMAN REVIEW"
