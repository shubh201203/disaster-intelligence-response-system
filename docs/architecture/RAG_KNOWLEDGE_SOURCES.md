# DIRS Grounded Knowledge Base & Emergency Source Registry

## Explicit Provenance Disclosure Statement

> **IMPORTANT PROVENANCE DISCLOSURE:**  
> *"The current development RAG corpus contains curated summaries with provenance metadata. Original official source documents are not claimed to be directly ingested. External source URLs are retained for provenance/reference purposes where available."*

---

## Authoritative Knowledge Sources & Provenance Registry

The DIRS Grounded Knowledge Base (`backend/app/ai/rag/service.py`) is populated with vetted emergency management guidelines from international and national disaster response organizations:

| Source ID | Organization | Document Title | Disaster Domain | Provenance Category | Source URL | URL Verification Status | Local Source File SHA-256 Checksum |
| :--- | :--- | :--- | :---: | :---: | :--- | :---: | :--- |
| **NDMA-CYC-2026** | **NDMA** (National Disaster Management Authority) | *DIRS Curated Summary — NDMA Cyclone Risk Mitigation Framework* | `CYCLONE` | `CURATED_SUMMARY` | [NDMA Cyclone Guidelines](https://ndma.gov.in/guidelines/cyclone) | `REFERENCE DOMAIN ONLY — UNVERIFIED` | `NOT_AVAILABLE — SOURCE FILE NOT LOCALLY INGESTED` |
| **FEMA-FLD-2026** | **FEMA** (Federal Emergency Management Agency) | *DIRS Curated Summary — FEMA Flood Emergency SOP* | `FLOOD` | `CURATED_SUMMARY` | [FEMA Flood SOP](https://fema.gov/disaster/flood-sop) | `REFERENCE DOMAIN ONLY — UNVERIFIED` | `NOT_AVAILABLE — SOURCE FILE NOT LOCALLY INGESTED` |
| **WHO-MED-2026** | **WHO** (World Health Organization) | *DIRS Curated Summary — WHO Emergency Medical Triage Guidelines* | `GENERAL` | `CURATED_SUMMARY` | [WHO First Aid Guidelines](https://who.int/emergencies/first-aid-guidelines) | `REFERENCE DOMAIN ONLY — UNVERIFIED` | `NOT_AVAILABLE — SOURCE FILE NOT LOCALLY INGESTED` |

---

## Document Chunking & Vector Schema

### Ingestion Pipeline
1. **Header-Preserving Text Chunker:** Parses markdown header hierarchies (`#`, `##`, `###`) to tag section titles (e.g. `Section 1: Pre-Evacuation Protocol`, `Section 2: Disaster Field Triage Protocol`).
2. **Chunk Size:** 500 tokens with 80 token overlap window.
3. **Embedding Vector:** Supports polymorphic `EmbeddingProvider` (`SEMANTIC_TRANSFORMER` 384-dimensional dense sentence embeddings or 128-dimensional L2-normalized `LEXICAL_HASH` fallback).

### Sample Chunk Structure
```json
{
  "document_id": "NDMA-CYC-2026",
  "chunk_index": 0,
  "section_title": "Section 1: Pre-Evacuation Protocol",
  "organization": "NDMA",
  "disaster_type": "CYCLONE",
  "text_content": "Upon issuance of Category 3 or Category 4 Cyclone warnings, local disaster management authorities must immediately establish pre-evacuation perimeters...",
  "embedding_vector": [0.084, 0.192, 0.000, 0.412, ...],
  "metadata_info": {
    "section": "Section 1: Pre-Evacuation Protocol",
    "source_provenance": "CURATED_SUMMARY",
    "publication_date": "2026-01-01",
    "access_date": "2026-09-15",
    "checksum": "NOT_AVAILABLE — SOURCE FILE NOT LOCALLY INGESTED",
    "runtime_text_hash": "a4f891b2c3d4e5f6",
    "url_verification_status": "REFERENCE DOMAIN ONLY — UNVERIFIED"
  }
}
```

---

## Ingestion & Index Maintenance

- **Seeding Execution:** Ingested via `RAGService.seed_authoritative_knowledge_base(db)`.
- **Reproducibility Script:** Verified using `python scripts/verify_rag_provenance.py`.
- **Idempotency:** Utilizes SHA-256 content hashing (`runtime_text_hash`) to avoid duplicate chunk creation on system restart.
