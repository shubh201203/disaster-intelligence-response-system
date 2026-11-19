import re
from typing import Tuple, Any
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from app.ai.duplicate_detection.features import haversine_distance_meters, time_difference_minutes

def compute_text_similarity(text1: str, text2: str) -> float:
    """
    Computes text similarity using TF-IDF cosine similarity, falling back to token Jaccard similarity if TF-IDF fails.
    """
    if not text1 or not text2:
        return 0.0
    
    t1_clean = re.sub(r'[^\w\s]', '', text1.lower()).strip()
    t2_clean = re.sub(r'[^\w\s]', '', text2.lower()).strip()
    
    if t1_clean == t2_clean:
        return 1.0
        
    try:
        vectorizer = TfidfVectorizer().fit([t1_clean, t2_clean])
        tfidf = vectorizer.transform([t1_clean, t2_clean])
        sim = float(cosine_similarity(tfidf[0:1], tfidf[1:2])[0][0])
        return min(1.0, max(0.0, sim))
    except Exception:
        # Fallback to Jaccard token overlap
        words1 = set(t1_clean.split())
        words2 = set(t2_clean.split())
        if not words1 or not words2:
            return 0.0
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        return intersection / float(union)

def calculate_multi_criteria_similarity(
    lat1: float, lng1: float, time1: Any, type1: str, text1: str,
    lat2: float, lng2: float, time2: Any, type2: str, text2: str
) -> Tuple[float, float, float, bool, float]:
    """
    Calculates composite multi-criteria similarity score (0.0 to 1.0) and individual metric breakdowns.
    Returns: (composite_similarity, distance_m, time_diff_min, type_match, text_sim)
    """
    dist_m = haversine_distance_meters(lat1, lng1, lat2, lng2)
    time_min = time_difference_minutes(time1, time2)
    type_match = type1.upper() == type2.upper()
    text_sim = compute_text_similarity(text1, text2)
    
    # 1. Distance score: 1.0 at 0m, drops to 0.0 at 1000m
    dist_score = max(0.0, 1.0 - (dist_m / 1000.0))
    
    # 2. Time score: 1.0 at 0min, drops to 0.0 at 120min
    time_score = max(0.0, 1.0 - (time_min / 120.0))
    
    # 3. Type score
    type_score = 1.0 if type_match else 0.0
    
    # Weighted composite similarity formula
    composite = (
        (dist_score * 0.40) +
        (time_score * 0.20) +
        (type_score * 0.20) +
        (text_sim * 0.20)
    )
    
    return round(float(composite), 3), round(dist_m, 1), round(time_min, 1), type_match, round(text_sim, 3)
