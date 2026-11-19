from typing import List, Dict, Any
from app.ai.duplicate_detection.similarity import calculate_multi_criteria_similarity
from app.ai.common.schemas import DuplicateCandidate, DuplicateEvidence

SIMILARITY_THRESHOLD: float = 0.55

def find_duplicate_candidates(
    target_incident: Any,
    candidate_incidents: List[Any]
) -> List[DuplicateCandidate]:
    """
    Evaluates candidate incidents against the target incident to find potential duplicates.
    Enforces human oversight: NEVER auto-deletes candidate reports.
    """
    candidates: List[DuplicateCandidate] = []
    
    t_text = f"{target_incident.title} {target_incident.description}"
    
    for cand in candidate_incidents:
        if cand.id == target_incident.id:
            continue
            
        c_text = f"{cand.title} {cand.description}"
        
        sim_score, dist_m, time_min, type_match, text_sim = calculate_multi_criteria_similarity(
            target_incident.latitude, target_incident.longitude, target_incident.created_at, target_incident.disaster_type, t_text,
            cand.latitude, cand.longitude, cand.created_at, cand.disaster_type, c_text
        )
        
        if sim_score >= SIMILARITY_THRESHOLD:
            recommendation = "POSSIBLE_DUPLICATE" if sim_score >= 0.70 else "RELATED_INCIDENT"
            candidates.append(
                DuplicateCandidate(
                    candidate_incident_id=cand.id,
                    candidate_code=cand.incident_code,
                    candidate_title=cand.title,
                    similarity_score=sim_score,
                    recommendation=recommendation,
                    evidence=DuplicateEvidence(
                        distance_m=dist_m,
                        time_difference_min=time_min,
                        type_match=type_match,
                        text_similarity=text_sim
                    )
                )
            )
            
    # Sort candidates by highest similarity score first
    candidates.sort(key=lambda c: c.similarity_score, reverse=True)
    return candidates
