# PolicyDocIQ Frontend

React + Vite interface for the PolicyDocIQ FastAPI backend.

## Run locally

Start the backend from the project root in Terminal 1:

```powershell
.venv\Scripts\activate
python -m uvicorn app.api:app --host 127.0.0.1 --port 8000
```

Do not use `--reload` while the API is using the local Qdrant database.

Start the frontend in Terminal 2:

```powershell
cd frontend
npm install
npm run dev
```

Open:

```text
http://localhost:5173
```

The frontend connects to `http://127.0.0.1:8000` and uses:

- `GET /health`
- `GET /collection`
- `POST /query`
- `GET /documents`
- `POST /documents/upload`
- `POST /documents/{document_id}/query`

## Upload and query a PDF

1. Choose a PDF in the **Upload a document** panel.
2. Select **Upload and Index** and wait for local BGE-M3 indexing.
3. Select **Use this document** from the indexed document list.
4. Ask a question. PolicyDocIQ will use the selected document endpoint.

Each uploaded PDF is stored under `data/uploaded_documents/`, with extracted
files under `outputs/documents/{document_id}/` and a separate Qdrant collection.

## Run the evaluation

Stop the FastAPI process first because local Qdrant storage supports one
accessing process at a time, then run from the project root:

```powershell
.venv\Scripts\activate
python scripts/05_run_evaluation.py
```

The evaluation reads the existing Qdrant collection without extracting or
re-indexing and writes:

- `outputs/evaluation_results.csv`
- `outputs/evaluation_summary.json`
