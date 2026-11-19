import os
from typing import Dict, Any

DEFAULT_CHUNK_SIZE_TOKENS = 600
DEFAULT_CHUNK_OVERLAP_TOKENS = 100

DEFAULT_RETRIEVAL_TOP_K = 5
MINIMUM_SIMILARITY_SCORE = 0.35

LLM_PROVIDER_NAME = os.environ.get("LLM_PROVIDER", "DIRS_GROUNDED_FALLBACK")
EMBEDDING_MODEL_NAME = os.environ.get("EMBEDDING_MODEL", "local-mini-lm-v2")

# Authoritative Government & Emergency Management Sources
AUTHORITATIVE_SOURCES = {
    "NDMA": "National Disaster Management Authority (Official Emergency Framework)",
    "FEMA": "Federal Emergency Management Agency (Disaster Operations Manual)",
    "WHO": "World Health Organization (Emergency Sanitation & Health Guidance)",
    "RED_CROSS": "International Red Cross (First Aid & Disaster Relief Standard Operating Procedures)",
    "GOVT_DEPT": "State Disaster Management Department (Evacuation & Rescue Protocols)",
    "INCOIS": "Indian National Centre for Ocean Information Services (Tsunami Early Warning)",
    "OSHA": "Occupational Safety and Health Administration (Chemical Hazard Protocol)"
}
