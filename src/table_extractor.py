import csv
import json
import re
from pathlib import Path
from typing import Any, Dict, List

import pdfplumber


TABLE_COLUMNS = [
    "document_id",
    "document_name",
    "table_id",
    "page_number",
    "table_index_on_page",
    "rows",
    "columns",
    "table_data",
    "table_text",
    "extraction_method",
]


def _clean_cell(value: Any) -> str:
    if value is None:
        return ""

    return re.sub(r"\s+", " ", str(value)).strip()


def _normalize_table(table: List[List[Any]]) -> List[List[str]]:
    rows = [[_clean_cell(cell) for cell in row] for row in (table or [])]
    rows = [row for row in rows if any(cell for cell in row)]

    if not rows:
        return []

    column_count = max(len(row) for row in rows)
    return [row + [""] * (column_count - len(row)) for row in rows]


def _flatten_table(table_data: List[List[str]]) -> str:
    return "\n".join(" | ".join(cell for cell in row) for row in table_data)


def _save_tables(
    tables: List[Dict[str, Any]],
    json_path: Path,
    csv_path: Path,
) -> None:
    with json_path.open("w", encoding="utf-8") as file:
        json.dump(tables, file, indent=2, ensure_ascii=False)
        file.write("\n")

    with csv_path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=TABLE_COLUMNS)
        writer.writeheader()

        for table in tables:
            row = dict(table)
            row["table_data"] = json.dumps(
                table["table_data"],
                ensure_ascii=False,
            )
            writer.writerow(row)


def extract_tables_from_pdf(
    pdf_path: str,
    document_id: str,
    output_dir: str,
) -> List[Dict[str, Any]]:
    """Extract PDF tables with pdfplumber and save JSON and CSV outputs."""

    source_path = Path(pdf_path)
    destination = Path(output_dir)

    if not source_path.exists():
        raise FileNotFoundError(f"PDF not found: {source_path}")

    if not document_id or not document_id.strip():
        raise ValueError("document_id must not be empty.")

    destination.mkdir(parents=True, exist_ok=True)
    json_path = destination / "tables.json"
    csv_path = destination / "tables.csv"
    tables: List[Dict[str, Any]] = []

    with pdfplumber.open(source_path) as pdf:
        for page_number, page in enumerate(pdf.pages, start=1):
            page_tables = page.extract_tables() or []

            for table_index, raw_table in enumerate(page_tables, start=1):
                table_data = _normalize_table(raw_table)
                if not table_data:
                    continue

                table_id = f"{document_id}_p{page_number}_t{table_index}"
                tables.append(
                    {
                        "document_id": document_id,
                        "document_name": source_path.name,
                        "table_id": table_id,
                        "page_number": page_number,
                        "table_index_on_page": table_index,
                        "rows": len(table_data),
                        "columns": max(len(row) for row in table_data),
                        "table_data": table_data,
                        "table_text": _flatten_table(table_data),
                        "extraction_method": "pdfplumber",
                    }
                )

    _save_tables(tables, json_path=json_path, csv_path=csv_path)
    return tables
