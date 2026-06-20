import sys
from pathlib import Path

from qdrant_client import QdrantClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.config import QDRANT_PATH


# Qdrant local mode is single-process. On Windows, only one Python process
# should access outputs/qdrant_db at a time. If locked, close the other terminal
# or kill the stale python.exe process before rerunning this script.


def main() -> None:
    print("PolicyDocIQ Step 3: inspect local Qdrant")
    print(f"Qdrant path: {QDRANT_PATH}")

    try:
        client = QdrantClient(path=str(QDRANT_PATH))
    except RuntimeError as error:
        raise RuntimeError(
            "Could not open local Qdrant storage. Another Python process may "
            "still be using outputs/qdrant_db. Close the other terminal or kill "
            "stale python.exe, then retry."
        ) from error

    collections = client.get_collections().collections

    if not collections:
        print("No collections found.")
        return

    print("\nCollections")
    print("-----------")

    for collection in collections:
        count = client.count(
            collection_name=collection.name,
            exact=True
        ).count
        print(f"{collection.name}: {count} points")


if __name__ == "__main__":
    main()
