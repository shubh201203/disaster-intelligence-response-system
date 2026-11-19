import re
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.rag import KnowledgeChunk, KnowledgeDocument
from app.ai.rag.embeddings.model import EmbeddingProvider, LocalEmbeddingModel

STOP_WORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are", 
    "as", "at", "be", "because", "been", "before", "being", "below", "between", "both", "but", 
    "by", "can", "could", "did", "do", "does", "doing", "down", "during", "each", "few", "for", 
    "from", "further", "had", "has", "have", "having", "he", "her", "here", "hers", "herself", 
    "him", "himself", "his", "how", "i", "if", "in", "into", "is", "it", "its", "itself", "just", 
    "me", "more", "most", "my", "myself", "no", "nor", "not", "of", "off", "on", "once", "only", 
    "or", "other", "ought", "our", "ours", "ourselves", "out", "over", "own", "same", "she", 
    "should", "so", "some", "such", "than", "that", "the", "their", "theirs", "them", "themselves", 
    "then", "there", "these", "they", "this", "those", "through", "to", "too", "under", "until", 
    "up", "very", "was", "we", "were", "what", "when", "where", "which", "while", "who", "whom", 
    "why", "with", "would", "you", "your", "yours", "yourself", "yourselves", "tell", "give", "please"
}

class HybridSearchRetriever:
    @classmethod
    def retrieve(
        cls,
        db: Session,
        query: str,
        disaster_type: Optional[str] = None,
        top_k: int = 5,
        semantic_weight: float = 0.50,
        lexical_weight: float = 0.50,
        embedding_provider_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Executes hybrid retrieval combining Vector Similarity + Lexical Keyword Matching + Hazard Metadata Filtering.
        `semantic_weight` and `lexical_weight` control hybrid scoring balance.
        """
        query_vec = EmbeddingProvider.encode(query, provider_type=embedding_provider_type)
        all_query_words = set(re.findall(r'\w+', query.lower()))
        meaningful_query_words = {w for w in all_query_words if w not in STOP_WORDS} or all_query_words

        # Base Query
        db_query = db.query(KnowledgeChunk, KnowledgeDocument).join(
            KnowledgeDocument, KnowledgeChunk.document_id == KnowledgeDocument.id
        )

        if disaster_type and disaster_type.upper() not in ["GENERAL", "ALL"]:
            db_query = db_query.filter(
                (KnowledgeDocument.disaster_type == disaster_type.upper()) |
                (KnowledgeDocument.disaster_type == "GENERAL")
            )

        results = db_query.all()
        scored_chunks = []

        for chunk, doc in results:
            sec_title = chunk.section_title or "Emergency Guidance"
            searchable_text = f"{doc.source_organization} {doc.title} {sec_title} {chunk.text_content}"

            # 1. Vector Similarity Score
            if chunk.embedding_vector:
                chunk_vec = chunk.embedding_vector
            else:
                chunk_vec = EmbeddingProvider.encode(searchable_text, provider_type=embedding_provider_type)
            semantic_score = EmbeddingProvider.cosine_similarity(query_vec, chunk_vec)

            # 2. Lexical Keyword Overlap Score (Content + Title + Metadata)
            chunk_words = set(re.findall(r'\w+', searchable_text.lower()))
            common_words = meaningful_query_words.intersection(chunk_words)
            lexical_score = len(common_words) / (len(meaningful_query_words) + 1e-6)

            # Metadata keyword alignment boost (organization or disaster type match)
            meta_boost = 0.0
            if doc.disaster_type.lower() in query.lower() or doc.source_organization.lower() in query.lower():
                meta_boost = 0.15

            # 3. Hybrid Weighted Score
            combined_score = min(1.0, (semantic_score * semantic_weight) + (lexical_score * lexical_weight) + meta_boost)

            scored_chunks.append({
                "chunk_id": chunk.id,
                "document_id": doc.id,
                "title": doc.title,
                "organization": doc.source_organization,
                "source_url": doc.source_url,
                "section": chunk.section_title or "Emergency Guidance",
                "text_content": chunk.text_content,
                "similarity_score": round(combined_score, 4),
                "semantic_score": round(semantic_score, 4),
                "lexical_score": round(lexical_score, 4),
                "disaster_type": doc.disaster_type,
                "document_type": doc.document_type
            })

        # Sort descending by score
        scored_chunks.sort(key=lambda x: x["similarity_score"], reverse=True)
        return scored_chunks[:top_k]
