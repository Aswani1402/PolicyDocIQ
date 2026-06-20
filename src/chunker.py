import re
from pathlib import Path
from typing import List, Dict, Optional

import pandas as pd


def clean_text(text: str) -> str:
    """
    Clean extracted PDF text without changing meaning.
    """

    if not isinstance(text, str):
        return ""

    text = text.replace("\x00", " ")
    text = re.sub(r"\s+", " ", text)
    text = text.strip()

    return text


def detect_section_title(text: str) -> Optional[str]:
    """
    Detect simple section-like headings from page text.

    This is not perfect, but it gives useful section metadata for retrieval.
    """

    if not isinstance(text, str) or not text.strip():
        return None

    lines = [line.strip() for line in text.splitlines() if line.strip()]

    for line in lines[:15]:
        clean_line = re.sub(r"\s+", " ", line).strip()

        if len(clean_line) < 4 or len(clean_line) > 120:
            continue

        is_upper = clean_line.upper() == clean_line
        starts_numbered = bool(re.match(r"^(\d+\.|[A-Z]\.|I\.|II\.|III\.|IV\.|V\.)\s+", clean_line))

        if is_upper or starts_numbered:
            return clean_line

    return None


def split_words_with_overlap(
    words: List[str],
    chunk_size: int,
    overlap: int
) -> List[List[str]]:
    """
    Split a list of words into overlapping word chunks.
    """

    if chunk_size <= overlap:
        raise ValueError("chunk_size must be greater than overlap")

    chunks = []
    start = 0

    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunks.append(words[start:end])

        if end == len(words):
            break

        start = end - overlap

    return chunks


def create_chunks_from_page(
    document_name: str,
    page_number: int,
    page_text: str,
    chunk_size: int = 350,
    overlap: int = 60
) -> List[Dict]:
    """
    Create chunks from one PDF page.
    """

    cleaned_text = clean_text(page_text)

    if not cleaned_text:
        return []

    words = cleaned_text.split()

    if not words:
        return []

    section_title = detect_section_title(page_text)

    word_chunks = split_words_with_overlap(
        words=words,
        chunk_size=chunk_size,
        overlap=overlap
    )

    page_chunks = []

    for local_chunk_index, chunk_words in enumerate(word_chunks, start=1):
        chunk_text = " ".join(chunk_words)

        page_chunks.append(
            {
                "document_name": document_name,
                "page_number": page_number,
                "local_chunk_index": local_chunk_index,
                "section_title": section_title,
                "chunk_type": "text",
                "text": chunk_text,
                "word_count": len(chunk_words),
                "char_count": len(chunk_text)
            }
        )

    return page_chunks


def build_chunks_from_pages(
    pages_df: pd.DataFrame,
    chunk_size: int = 350,
    overlap: int = 60
) -> pd.DataFrame:
    """
    Build page-aware chunks from extracted PDF pages.
    """

    required_columns = {"document_name", "page_number", "text"}

    missing_columns = required_columns - set(pages_df.columns)
    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")

    all_chunks = []

    for _, row in pages_df.iterrows():
        page_chunks = create_chunks_from_page(
            document_name=row["document_name"],
            page_number=int(row["page_number"]),
            page_text=row["text"],
            chunk_size=chunk_size,
            overlap=overlap
        )

        all_chunks.extend(page_chunks)

    chunks_df = pd.DataFrame(all_chunks)

    if len(chunks_df) == 0:
        return chunks_df

    chunks_df.insert(
        0,
        "chunk_id",
        [f"chunk_{i}" for i in range(1, len(chunks_df) + 1)]
    )

    return chunks_df


def save_chunks(chunks_df: pd.DataFrame, output_path: str) -> None:
    """
    Save chunks to CSV.
    """

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    chunks_df.to_csv(path, index=False, encoding="utf-8-sig")