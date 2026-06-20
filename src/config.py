from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

PDF_PATH = PROJECT_ROOT / "data" / "Qatar_Test_Document.pdf"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
EXTRACTED_PAGES_PATH = OUTPUTS_DIR / "extracted_pages.csv"
DOCLING_MD_PATH = OUTPUTS_DIR / "docling_output.md"
EXTRACTED_CHUNKS_PATH = OUTPUTS_DIR / "extracted_chunks.csv"

# Qdrant local mode is single-process. On Windows, only one Python process
# should access this folder at a time. If it stays locked, close the terminal
# running PolicyDocIQ or kill the stale python.exe process.
QDRANT_PATH = OUTPUTS_DIR / "qdrant_db"
QDRANT_COLLECTION_NAME = "policydociq_qatar"

EMBEDDING_MODEL_NAME = "BAAI/bge-m3"
EMBEDDING_DEVICE = "cpu"
