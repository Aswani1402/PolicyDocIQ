import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOCUMENTS_DIR = PROJECT_ROOT / "data" / "uploaded_documents"
OUTPUTS_DIR = PROJECT_ROOT / "outputs" / "documents"
REGISTRY_PATH = PROJECT_ROOT / "outputs" / "documents_registry.json"


def ensure_document_dirs() -> None:
    DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)


def slugify_filename(filename: str) -> str:
    name = Path(filename).stem.lower()
    name = re.sub(r"[^a-z0-9]+", "_", name)
    name = name.strip("_")

    if not name:
        name = "document"

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    return f"{name}_{timestamp}"


def collection_name_from_document_id(document_id: str) -> str:
    safe_id = re.sub(r"[^a-zA-Z0-9_]", "_", document_id)
    return f"policydociq_{safe_id}"


def load_registry() -> Dict:
    ensure_document_dirs()

    if not REGISTRY_PATH.exists():
        return {"documents": []}

    with open(REGISTRY_PATH, "r", encoding="utf-8") as file:
        return json.load(file)


def save_registry(registry: Dict) -> None:
    ensure_document_dirs()

    with open(REGISTRY_PATH, "w", encoding="utf-8") as file:
        json.dump(registry, file, indent=2, ensure_ascii=False)


def add_document_record(record: Dict) -> None:
    registry = load_registry()

    registry["documents"] = [
        doc for doc in registry["documents"]
        if doc["document_id"] != record["document_id"]
    ]

    registry["documents"].append(record)
    save_registry(registry)


def list_documents() -> List[Dict]:
    registry = load_registry()
    return registry.get("documents", [])


def get_document(document_id: str) -> Optional[Dict]:
    documents = list_documents()

    for document in documents:
        if document["document_id"] == document_id:
            return document

    return None
