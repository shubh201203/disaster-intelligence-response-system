import re
from typing import List, Dict, Any

def chunk_text_content(
    text: str,
    chunk_size_tokens: int = 600,
    chunk_overlap_tokens: int = 100
) -> List[Dict[str, Any]]:
    """
    Chunks document text into token-bounded sections while preserving section headings and titles.
    Approximate word-to-token ratio: 1 word ~ 1.3 tokens.
    """
    clean_text = re.sub(r'\r\n', '\n', text).strip()
    paragraphs = clean_text.split('\n\n')

    chunks = []
    current_chunk_paragraphs = []
    current_word_count = 0
    target_word_count = int(chunk_size_tokens / 1.3)
    overlap_word_count = int(chunk_overlap_tokens / 1.3)
    current_section = "General Guidance"

    for para in paragraphs:
        para_clean = para.strip()
        if not para_clean:
            continue

        # Detect Markdown headers as section titles
        if para_clean.startswith("#"):
            first_line = para_clean.split("\n")[0]
            header_title = first_line.lstrip("#").strip()
            current_section = header_title[:250]

        words = para_clean.split()
        para_word_count = len(words)

        if current_word_count + para_word_count > target_word_count and current_chunk_paragraphs:
            chunk_body = "\n\n".join(current_chunk_paragraphs)
            approx_tokens = int(len(chunk_body.split()) * 1.3)
            chunks.append({
                "section_title": current_section,
                "text_content": chunk_body,
                "token_count": approx_tokens
            })

            # Retain overlap from end of current chunk
            overlap_words = chunk_body.split()[-overlap_word_count:] if len(chunk_body.split()) > overlap_word_count else []
            current_chunk_paragraphs = [" ".join(overlap_words), para_clean] if overlap_words else [para_clean]
            current_word_count = len(" ".join(current_chunk_paragraphs).split())
        else:
            current_chunk_paragraphs.append(para_clean)
            current_word_count += para_word_count

    if current_chunk_paragraphs:
        chunk_body = "\n\n".join(current_chunk_paragraphs)
        approx_tokens = int(len(chunk_body.split()) * 1.3)
        chunks.append({
            "section_title": current_section,
            "text_content": chunk_body,
            "token_count": approx_tokens
        })

    return chunks
