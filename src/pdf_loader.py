from pathlib import Path
from typing import Optional

import fitz  # PyMuPDF
import pandas as pd

try:
    from docling.document_converter import DocumentConverter
except ImportError:
    DocumentConverter = None


def validate_pdf_path(pdf_path: str) -> Path:
    """
    Validate that the input PDF exists.
    """

    path = Path(pdf_path)

    if not path.exists():
        raise FileNotFoundError(f"PDF file not found: {path}")

    if path.suffix.lower() != ".pdf":
        raise ValueError(f"Expected a PDF file, got: {path.suffix}")

    return path


def extract_pages_with_pymupdf(pdf_path: str) -> pd.DataFrame:
    """
    Extract page-wise text using PyMuPDF.

    This is important because every chunk and answer must preserve page numbers.
    """

    path = validate_pdf_path(pdf_path)

    document = fitz.open(path)
    extracted_pages = []

    for page_index in range(len(document)):
        page = document[page_index]
        text = page.get_text("text")

        extracted_pages.append(
            {
                "document_name": path.name,
                "page_number": page_index + 1,
                "text": text.strip(),
                "char_count": len(text.strip()),
                "word_count": len(text.strip().split()),
                "extraction_method": "pymupdf"
            }
        )

    document.close()

    return pd.DataFrame(extracted_pages)


def extract_docling_markdown(pdf_path: str) -> Optional[str]:
    """
    Extract structured document content using Docling and return Markdown.

    This gives us a more structured representation of the PDF.
    Later, we will use this for section-aware chunking and table handling.
    """

    if DocumentConverter is None:
        print("Docling is not installed. Skipping Docling extraction.")
        return None

    path = validate_pdf_path(pdf_path)

    converter = DocumentConverter()
    result = converter.convert(str(path))
    doc = result.document

    markdown_text = doc.export_to_markdown()
    return markdown_text


def save_dataframe(df: pd.DataFrame, output_path: str) -> None:
    """
    Save dataframe as CSV.
    """

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    df.to_csv(path, index=False, encoding="utf-8-sig")


def save_text(text: str, output_path: str) -> None:
    """
    Save plain text / markdown output.
    """

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    path.write_text(text, encoding="utf-8")

def load_pdf(
    pdf_path: str,
    pages_csv_path: str = "outputs/extracted_pages.csv",
    docling_md_path: str = "outputs/docling_output.md",
    run_docling: bool = False
) -> pd.DataFrame:
    """
    Main PDF loading function.

    Outputs:
    1. outputs/extracted_pages.csv
       - page-wise text with page numbers

    2. outputs/docling_output.md
       - optional Docling structured markdown output
    """

    print("Starting page-wise PDF extraction with PyMuPDF...")
    pages_df = extract_pages_with_pymupdf(pdf_path)
    save_dataframe(pages_df, pages_csv_path)

    print(f"Saved page-wise extraction to: {pages_csv_path}")
    print(f"Total pages extracted: {len(pages_df)}")

    if run_docling:
        print("Starting Docling structured extraction...")
        try:
            markdown_text = extract_docling_markdown(pdf_path)

            if markdown_text:
                save_text(markdown_text, docling_md_path)
                print(f"Saved Docling markdown to: {docling_md_path}")
            else:
                print("Docling markdown was not created.")

        except Exception as error:
            print("Docling extraction failed, but PyMuPDF extraction succeeded.")
            print(f"Docling error: {error}")
    else:
        print("Skipping Docling for now. We will use it later for table/layout extraction.")

    return pages_df
