import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.table_extractor import extract_tables_from_pdf


def main():
    pdf_path = PROJECT_ROOT / "data" / "Qatar_Test_Document.pdf"
    output_dir = PROJECT_ROOT / "outputs" / "tables" / "qatar_default"

    tables = extract_tables_from_pdf(
        pdf_path=str(pdf_path),
        document_id="qatar_default",
        output_dir=str(output_dir),
    )
    pages = sorted({table["page_number"] for table in tables})

    print(f"Total tables: {len(tables)}")
    print(f"Pages with tables: {pages}")
    print(f"JSON output: {output_dir / 'tables.json'}")
    print(f"CSV output: {output_dir / 'tables.csv'}")


if __name__ == "__main__":
    main()
