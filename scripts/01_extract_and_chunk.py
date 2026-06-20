import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.chunker import build_chunks_from_pages, save_chunks
from src.config import DOCLING_MD_PATH, EXTRACTED_CHUNKS_PATH, EXTRACTED_PAGES_PATH, PDF_PATH
from src.pdf_loader import load_pdf


def main() -> None:
    print("PolicyDocIQ Step 1: extract PDF pages and build chunks")
    print(f"PDF: {PDF_PATH}")

    pages_df = load_pdf(
        pdf_path=str(PDF_PATH),
        pages_csv_path=str(EXTRACTED_PAGES_PATH),
        docling_md_path=str(DOCLING_MD_PATH),
        run_docling=False
    )

    print("\nExtraction summary")
    print("------------------")
    print("Total pages:", len(pages_df))
    print("Total words:", int(pages_df["word_count"].sum()))
    print("Total characters:", int(pages_df["char_count"].sum()))

    print("\nCreating page-aware chunks...")
    chunks_df = build_chunks_from_pages(
        pages_df=pages_df,
        chunk_size=350,
        overlap=60
    )

    save_chunks(chunks_df, str(EXTRACTED_CHUNKS_PATH))

    print("\nChunking summary")
    print("----------------")
    print("Total chunks:", len(chunks_df))
    print("Saved chunks to:", EXTRACTED_CHUNKS_PATH)


if __name__ == "__main__":
    main()
