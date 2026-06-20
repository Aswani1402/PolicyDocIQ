import { useCallback, useEffect, useState } from 'react'
import './App.css'

const API_BASE_URL = 'http://127.0.0.1:8000'
const EVIDENCE_PREVIEW_LENGTH = 700

const SAMPLE_QUESTIONS = [
  "What is Qatar's projected GDP growth for 2024 and 2025?",
  "What are the main risks to Qatar's economic outlook?",
  'What does the report say about VAT?',
  "Summarize Qatar's banking sector condition.",
  'What does the report say about LNG expansion?',
]

async function fetchBackendStatus() {
  try {
    const [healthResponse, collectionResponse] = await Promise.all([
      fetch(`${API_BASE_URL}/health`),
      fetch(`${API_BASE_URL}/collection`),
    ])

    if (!healthResponse.ok || !collectionResponse.ok) {
      throw new Error('The backend returned an unsuccessful response.')
    }

    const [health, collection] = await Promise.all([
      healthResponse.json(),
      collectionResponse.json(),
    ])

    if (health.status !== 'ok') {
      throw new Error('The backend health check did not return OK.')
    }

    return {
      loading: false,
      connected: true,
      collectionName: collection.collection_name ?? '—',
      points: collection.points ?? '—',
      error: '',
    }
  } catch (error) {
    return {
      loading: false,
      connected: false,
      collectionName: '—',
      points: '—',
      error:
        error instanceof Error
          ? error.message
          : 'Could not connect to the PolicyDocIQ API.',
    }
  }
}

let initialConnectionRequest
let initialDocumentsRequest

function getInitialBackendStatus() {
  if (!initialConnectionRequest) {
    initialConnectionRequest = fetchBackendStatus()
  }

  return initialConnectionRequest
}

async function fetchDocuments() {
  const response = await fetch(`${API_BASE_URL}/documents`)
  const data = await response.json().catch(() => null)

  if (!response.ok) {
    throw new Error(
      data?.detail || `Document list failed with status ${response.status}.`,
    )
  }

  return Array.isArray(data?.documents) ? data.documents : []
}

function getInitialDocuments() {
  if (!initialDocumentsRequest) {
    initialDocumentsRequest = fetchDocuments()
  }

  return initialDocumentsRequest
}

function StatusIcon({ connected }) {
  return (
    <span className={`status-dot ${connected ? 'is-connected' : ''}`} aria-hidden="true">
      <span />
    </span>
  )
}

function DocumentIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M7 3.75h7.8L19 7.95v12.3H7V3.75Z" />
      <path d="M14.5 3.75v4.5H19M10 12h6M10 15.5h6" />
    </svg>
  )
}

function SearchIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <circle cx="11" cy="11" r="6.25" />
      <path d="m16 16 4 4" />
    </svg>
  )
}

function SparkleIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M12 2.75c.55 4.85 3.4 7.7 8.25 8.25-4.85.55-7.7 3.4-8.25 8.25C11.45 14.4 8.6 11.55 3.75 11 8.6 10.45 11.45 7.6 12 2.75Z" />
    </svg>
  )
}

function ArrowIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M5 12h14M14 7l5 5-5 5" />
    </svg>
  )
}

function CopyIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <rect x="8" y="8" width="11" height="11" rx="2" />
      <path d="M16 8V6a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h2" />
    </svg>
  )
}

function UploadIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M12 16V4M7.5 8.5 12 4l4.5 4.5M5 14v5h14v-5" />
    </svg>
  )
}

function RefreshIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M19 8a7 7 0 1 0 1 6M19 4v4h-4" />
    </svg>
  )
}

function TableIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <rect x="3.5" y="5" width="17" height="14" rx="2" />
      <path d="M3.5 10h17M9 5v14M15 5v14" />
    </svg>
  )
}

function formatUploadedAt(value) {
  if (!value) return '—'

  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString()
}

function isTableHeavy(text = '') {
  const lineCount = text.split(/\r?\n/).length
  const separatorCount = (text.match(/[|;]/g) || []).length
  const numberCount = (text.match(/\d+(?:\.\d+)?/g) || []).length

  return lineCount > 8 || separatorCount > 10 || numberCount > 28
}

function EvidenceCard({ item, index, expanded, onToggle }) {
  const text = item.text || 'No excerpt text returned.'
  const canExpand = text.length > EVIDENCE_PREVIEW_LENGTH
  const displayText =
    canExpand && !expanded
      ? `${text.slice(0, EVIDENCE_PREVIEW_LENGTH).trimEnd()}…`
      : text

  return (
    <article className={`evidence-card ${isTableHeavy(text) ? 'table-heavy' : ''}`}>
      <div className="evidence-rank">Rank {index + 1}</div>
      <div className="evidence-content">
        <div className="evidence-meta">
          <span className="page-badge">Page {item.page_number ?? '—'}</span>
          <span>
            Score{' '}
            <strong>
              {typeof item.score === 'number' ? item.score.toFixed(4) : '—'}
            </strong>
          </span>
          {typeof item.retrieval_score === 'number' && (
            <span>
              Retrieval <strong>{item.retrieval_score.toFixed(4)}</strong>
            </span>
          )}
          {typeof item.rerank_score === 'number' && (
            <span>
              Rerank <strong>{item.rerank_score.toFixed(4)}</strong>
            </span>
          )}
          {item.document_name && (
            <span className="document-name" title={item.document_name}>
              {item.document_name}
            </span>
          )}
        </div>
        <h3>{item.section_title || 'Report excerpt'}</h3>
        <div className="evidence-text">{displayText}</div>
        {canExpand && (
          <button className="expand-button" type="button" onClick={onToggle}>
            {expanded ? 'Show less' : 'Show more'}
          </button>
        )}
      </div>
    </article>
  )
}

function App() {
  const [question, setQuestion] = useState('')
  const [topK, setTopK] = useState(5)
  const [useReranker, setUseReranker] = useState(true)
  const [rerankPool, setRerankPool] = useState(20)
  const [connection, setConnection] = useState({
    loading: true,
    connected: false,
    collectionName: '—',
    points: '—',
    error: '',
  })
  const [result, setResult] = useState(null)
  const [queryState, setQueryState] = useState({
    loading: false,
    error: '',
  })
  const [expandedEvidence, setExpandedEvidence] = useState({})
  const [copyState, setCopyState] = useState('idle')
  const [documents, setDocuments] = useState([])
  const [documentsState, setDocumentsState] = useState({
    loading: true,
    error: '',
  })
  const [activeDocument, setActiveDocument] = useState(null)
  const [selectedFile, setSelectedFile] = useState(null)
  const [fileInputKey, setFileInputKey] = useState(0)
  const [uploadState, setUploadState] = useState({
    loading: false,
    message: '',
    error: '',
  })
  const [tableQuery, setTableQuery] = useState('')
  const [tables, setTables] = useState([])
  const [tableState, setTableState] = useState({
    loading: false,
    loaded: false,
    error: '',
  })

  const checkConnection = useCallback(async () => {
    setConnection((current) => ({ ...current, loading: true, error: '' }))
    setConnection(await fetchBackendStatus())
  }, [])

  useEffect(() => {
    let isActive = true

    getInitialBackendStatus().then((status) => {
      if (isActive) {
        setConnection(status)
      }
    })

    return () => {
      isActive = false
    }
  }, [])

  useEffect(() => {
    let isActive = true

    getInitialDocuments()
      .then((items) => {
        if (isActive) {
          setDocuments(items)
          setDocumentsState({ loading: false, error: '' })
        }
      })
      .catch((error) => {
        if (isActive) {
          setDocumentsState({
            loading: false,
            error:
              error instanceof TypeError
                ? 'Could not reach the backend to load documents.'
                : error.message,
          })
        }
      })

    return () => {
      isActive = false
    }
  }, [])

  const refreshDocuments = async () => {
    setDocumentsState({ loading: true, error: '' })

    try {
      const items = await fetchDocuments()
      setDocuments(items)
      setDocumentsState({ loading: false, error: '' })

      if (
        activeDocument &&
        !items.some((item) => item.document_id === activeDocument.document_id)
      ) {
        setActiveDocument(null)
        clearResult()
        clearTableResults()
      }
    } catch (error) {
      setDocumentsState({
        loading: false,
        error:
          error instanceof TypeError
            ? 'Could not reach the backend to refresh documents.'
            : error.message,
      })
    }
  }

  const handleFileChange = (event) => {
    const file = event.target.files?.[0] ?? null

    if (file && !file.name.toLowerCase().endsWith('.pdf')) {
      setSelectedFile(null)
      setUploadState({
        loading: false,
        message: '',
        error: 'Only PDF files are supported.',
      })
      setFileInputKey((current) => current + 1)
      return
    }

    setSelectedFile(file)
    setUploadState({ loading: false, message: '', error: '' })
  }

  const handleUpload = async (event) => {
    event.preventDefault()

    if (!selectedFile) {
      setUploadState({
        loading: false,
        message: '',
        error: 'Choose a PDF file before uploading.',
      })
      return
    }

    setUploadState({
      loading: true,
      message: 'Uploading, extracting, and indexing with local BGE-M3…',
      error: '',
    })

    const formData = new FormData()
    formData.append('file', selectedFile)

    try {
      const response = await fetch(`${API_BASE_URL}/documents/upload`, {
        method: 'POST',
        body: formData,
      })
      const data = await response.json().catch(() => null)

      if (!response.ok) {
        throw new Error(
          data?.detail || `Upload failed with status ${response.status}.`,
        )
      }

      const uploadedDocument = data?.document
      setUploadState({
        loading: false,
        message: data?.message || 'Document uploaded and indexed successfully.',
        error: '',
      })
      setSelectedFile(null)
      setFileInputKey((current) => current + 1)

      const items = await fetchDocuments()
      setDocuments(items)
      setDocumentsState({ loading: false, error: '' })

      if (uploadedDocument) {
        setActiveDocument(uploadedDocument)
        clearResult()
        clearTableResults()
      }
    } catch (error) {
      setUploadState({
        loading: false,
        message: '',
        error:
          error instanceof TypeError
            ? `Could not reach the backend at ${API_BASE_URL}.`
            : error.message,
      })
    }
  }

  const handleSubmit = async (event) => {
    event.preventDefault()

    const trimmedQuestion = question.trim()
    if (trimmedQuestion.length < 3) {
      setQueryState({
        loading: false,
        error: 'Enter a question with at least 3 characters.',
      })
      return
    }

    setQueryState({ loading: true, error: '' })
    setResult(null)
    setExpandedEvidence({})
    setCopyState('idle')

    try {
      const queryPath = activeDocument
        ? `/documents/${encodeURIComponent(activeDocument.document_id)}/query`
        : '/query'
      const response = await fetch(`${API_BASE_URL}${queryPath}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          question: trimmedQuestion,
          top_k: Number(topK),
          use_reranker: useReranker,
          rerank_pool: Number(rerankPool),
        }),
      })

      const data = await response.json().catch(() => null)

      if (!response.ok) {
        throw new Error(
          data?.detail || `Query failed with status ${response.status}.`,
        )
      }

      setResult(data)
      setQueryState({ loading: false, error: '' })
    } catch (error) {
      const message =
        error instanceof TypeError
          ? `Could not reach the backend at ${API_BASE_URL}. Start FastAPI and try again.`
          : error instanceof Error
            ? error.message
            : 'The query could not be completed.'

      setQueryState({
        loading: false,
        error: message,
      })
    }
  }

  const clearResult = () => {
    setResult(null)
    setQueryState({ loading: false, error: '' })
    setExpandedEvidence({})
    setCopyState('idle')
  }

  const clearTableResults = () => {
    setTableQuery('')
    setTables([])
    setTableState({ loading: false, loaded: false, error: '' })
  }

  const copyAnswer = async () => {
    if (!result?.answer) return

    try {
      await navigator.clipboard.writeText(result.answer)
      setCopyState('copied')
    } catch {
      setCopyState('error')
    }
  }

  const loadTables = async (searchQuery = '') => {
    if (!activeDocument) return

    setTableState({ loading: true, loaded: false, error: '' })

    const encodedDocumentId = encodeURIComponent(activeDocument.document_id)
    const path = searchQuery.trim()
      ? `/documents/${encodedDocumentId}/tables/search?query=${encodeURIComponent(searchQuery.trim())}`
      : `/documents/${encodedDocumentId}/tables`

    try {
      const response = await fetch(`${API_BASE_URL}${path}`)
      const data = await response.json().catch(() => null)

      if (!response.ok) {
        throw new Error(
          data?.detail || `Table request failed with status ${response.status}.`,
        )
      }

      setTables(Array.isArray(data?.tables) ? data.tables : [])
      setTableState({ loading: false, loaded: true, error: '' })
    } catch (error) {
      setTables([])
      setTableState({
        loading: false,
        loaded: false,
        error:
          error instanceof TypeError
            ? `Could not reach the backend at ${API_BASE_URL}.`
            : error.message,
      })
    }
  }

  const handleTableSearch = (event) => {
    event.preventDefault()

    if (!tableQuery.trim()) {
      loadTables()
      return
    }

    loadTables(tableQuery)
  }

  const connected = connection.connected && !connection.loading
  const activeDocumentLabel = activeDocument
    ? activeDocument.filename
    : 'Default Qatar report'

  return (
    <div className="app-shell">
      <header className="site-header">
        <div className="header-inner">
          <a className="brand" href="/" aria-label="PolicyDocIQ home">
            <span className="brand-mark">
              <DocumentIcon />
            </span>
            <span>PolicyDocIQ</span>
          </a>
          <div className={`header-status ${connected ? 'connected' : ''}`}>
            <StatusIcon connected={connected} />
            {connection.loading
              ? 'Checking API'
              : connected
                ? 'API Connected'
                : 'API Offline'}
          </div>
        </div>
      </header>

      <main>
        <section className="hero-section">
          <div className="eyebrow">
            <span>IMF Research Workspace</span>
          </div>
          <h1>Policy intelligence you can verify.</h1>
          <p>
            Citation-backed RAG for IMF Article IV Reports
          </p>
        </section>

        <section className="status-card" aria-label="Backend and document status">
          <div className="status-summary">
            <div className="status-icon-wrap">
              <StatusIcon connected={connected} />
            </div>
            <div>
              <span className="label">Backend status</span>
              <strong>
                {connection.loading
                  ? 'Connecting…'
                  : connected
                    ? 'Connected'
                    : 'Not connected'}
              </strong>
            </div>
          </div>
          <div className="status-metric">
            <span className="label">Default collection</span>
            <strong title={String(connection.collectionName)}>
              {connection.collectionName}
            </strong>
          </div>
          <div className="status-metric">
            <span className="label">Indexed chunks</span>
            <strong>{connection.points}</strong>
          </div>
          <div className="status-metric active-document-metric">
            <span className="label">Active document</span>
            <strong title={activeDocumentLabel}>{activeDocumentLabel}</strong>
          </div>
          {!connection.loading && !connected && (
            <button className="retry-button" type="button" onClick={checkConnection}>
              Retry
            </button>
          )}
        </section>

        {connection.error && !connected && (
          <div className="notice error-notice" role="alert">
            <strong>Backend unavailable.</strong>
            <span>
              Start FastAPI at {API_BASE_URL}, then retry the connection.
            </span>
          </div>
        )}

        <section className="metadata-panel" aria-label="Project metadata">
          {[
            ['Model', 'BGE-M3'],
            ['Vector DB', 'Qdrant'],
            ['Backend', 'FastAPI'],
            ['Frontend', 'React + Vite'],
            ['Citation mode', 'Page-level evidence'],
          ].map(([label, value]) => (
            <div className="metadata-item" key={label}>
              <span>{label}</span>
              <strong>{value}</strong>
            </div>
          ))}
        </section>

        <section className="document-workspace">
          <article className="upload-card">
            <div className="section-heading">
              <span className="section-icon">
                <UploadIcon />
              </span>
              <div>
                <h2>Upload a document</h2>
                <p>Create a separate searchable collection for a PDF.</p>
              </div>
            </div>

            <form className="upload-form" onSubmit={handleUpload}>
              <label className="file-picker" htmlFor="pdf-upload">
                <span>{selectedFile ? selectedFile.name : 'Choose PDF'}</span>
                <input
                  key={fileInputKey}
                  id="pdf-upload"
                  type="file"
                  accept=".pdf,application/pdf"
                  onChange={handleFileChange}
                  disabled={uploadState.loading}
                />
              </label>
              <button
                className="upload-button"
                type="submit"
                disabled={uploadState.loading || !selectedFile}
              >
                {uploadState.loading ? (
                  <>
                    <span className="spinner" aria-hidden="true" />
                    Uploading and indexing
                  </>
                ) : (
                  <>
                    <UploadIcon />
                    Upload and Index
                  </>
                )}
              </button>
            </form>

            <p className="upload-help">
              Indexing may take several minutes because BGE-M3 runs locally.
              Keep the backend process running and do not use <code>--reload</code>.
            </p>

            {(uploadState.message || uploadState.error) && (
              <div
                className={`inline-message ${uploadState.error ? 'is-error' : 'is-success'}`}
                role="status"
              >
                {uploadState.error || uploadState.message}
              </div>
            )}
          </article>

          <article className="documents-card">
            <div className="documents-header">
              <div>
                <h2>Indexed documents</h2>
                <p>Select which uploaded PDF should answer questions.</p>
              </div>
              <button
                className="secondary-button"
                type="button"
                onClick={refreshDocuments}
                disabled={documentsState.loading || uploadState.loading}
              >
                <RefreshIcon />
                {documentsState.loading ? 'Refreshing' : 'Refresh documents'}
              </button>
            </div>

            <button
              className={`default-document ${!activeDocument ? 'is-active' : ''}`}
              type="button"
              onClick={() => {
                setActiveDocument(null)
                clearResult()
                clearTableResults()
              }}
            >
              <span>
                <strong>Default Qatar report</strong>
                <small>{connection.collectionName}</small>
              </span>
              <span>{!activeDocument ? 'Active' : 'Use default'}</span>
            </button>

            {documentsState.error && (
              <div className="inline-message is-error">{documentsState.error}</div>
            )}

            {!documentsState.loading && !documentsState.error && documents.length === 0 && (
              <div className="empty-documents">
                No uploaded documents yet. Choose a PDF to create one.
              </div>
            )}

            <div className="document-list">
              {documents.map((document) => {
                const isActive =
                  activeDocument?.document_id === document.document_id

                return (
                  <div
                    className={`document-card ${isActive ? 'is-active' : ''}`}
                    key={document.document_id}
                  >
                    <div className="document-card-heading">
                      <div>
                        <strong title={document.filename}>{document.filename}</strong>
                        <code>{document.document_id}</code>
                      </div>
                      <button
                        type="button"
                        onClick={() => {
                          setActiveDocument(document)
                          clearResult()
                          clearTableResults()
                        }}
                        disabled={isActive}
                      >
                        {isActive ? 'Active' : 'Use this document'}
                      </button>
                    </div>
                    <dl>
                      <div>
                        <dt>Pages</dt>
                        <dd>{document.pages ?? '—'}</dd>
                      </div>
                      <div>
                        <dt>Chunks</dt>
                        <dd>{document.chunks ?? '—'}</dd>
                      </div>
                      <div>
                        <dt>Qdrant points</dt>
                        <dd>{document.qdrant_points ?? '—'}</dd>
                      </div>
                      <div>
                        <dt>Uploaded</dt>
                        <dd>{formatUploadedAt(document.uploaded_at)}</dd>
                      </div>
                      <div>
                        <dt>Tables</dt>
                        <dd>{document.table_count ?? 0}</dd>
                      </div>
                    </dl>
                  </div>
                )
              })}
            </div>
          </article>
        </section>

        <section className="table-intelligence-card">
          <div className="table-intelligence-header">
            <div className="section-heading compact">
              <span className="section-icon accent">
                <TableIcon />
              </span>
              <div>
                <h2>Table Intelligence</h2>
                <p>Inspect and search tables extracted with pdfplumber.</p>
              </div>
            </div>
            {activeDocument && (
              <span className="table-count-badge">
                {activeDocument.table_count ?? 0} tables
              </span>
            )}
          </div>

          {!activeDocument ? (
            <div className="table-empty-state">
              Select or upload a document to view extracted tables.
            </div>
          ) : (
            <>
              <div className="table-toolbar">
                <button
                  className="secondary-button"
                  type="button"
                  onClick={() => loadTables()}
                  disabled={tableState.loading}
                >
                  <TableIcon />
                  View extracted tables
                </button>

                <form className="table-search-form" onSubmit={handleTableSearch}>
                  <input
                    type="search"
                    value={tableQuery}
                    onChange={(event) => setTableQuery(event.target.value)}
                    placeholder="Search tables, for example GDP"
                    disabled={tableState.loading}
                  />
                  <button
                    className="secondary-button"
                    type="submit"
                    disabled={tableState.loading}
                  >
                    <SearchIcon />
                    Search tables
                  </button>
                </form>
              </div>

              {tableState.error && (
                <div className="inline-message is-error">{tableState.error}</div>
              )}

              {tableState.loading && (
                <div className="table-empty-state">Loading extracted tables…</div>
              )}

              {tableState.loaded && tables.length === 0 && (
                <div className="table-empty-state">
                  No matching extracted tables were found.
                </div>
              )}

              {tables.length > 0 && (
                <div className="table-results">
                  {tables.map((table) => (
                    <details className="table-result-card" key={table.table_id}>
                      <summary>
                        <span>
                          <strong>{table.table_id}</strong>
                          <small>Page {table.page_number ?? '—'}</small>
                        </span>
                        <span>
                          {table.rows ?? '—'} rows · {table.columns ?? '—'} columns
                        </span>
                      </summary>
                      <div className="table-preview">
                        {(table.table_data ?? []).slice(0, 6).map((row, rowIndex) => (
                          <div className="table-preview-row" key={`${table.table_id}-${rowIndex}`}>
                            {row.map((cell, cellIndex) => (
                              <span key={`${table.table_id}-${rowIndex}-${cellIndex}`}>
                                {cell || '—'}
                              </span>
                            ))}
                          </div>
                        ))}
                        {!table.table_data?.length && (
                          <pre>{table.table_text || 'No table preview available.'}</pre>
                        )}
                      </div>
                    </details>
                  ))}
                </div>
              )}
            </>
          )}
        </section>

        <section className="query-card">
          <div className="section-heading">
            <span className="section-icon">
              <SearchIcon />
            </span>
            <div>
              <h2>Ask the report</h2>
              <p>
                Active source: <strong>{activeDocumentLabel}</strong>. Answers are
                grounded only in retrieved document evidence.
              </p>
            </div>
          </div>

          <form onSubmit={handleSubmit}>
            <label htmlFor="question">Your question</label>
            <textarea
              id="question"
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder="Ask about Qatar's economic outlook, fiscal policy, banking sector…"
              rows="4"
              disabled={queryState.loading}
            />

            <div className="retrieval-controls">
              <div className="mode-summary">
                <span>Current mode</span>
                <strong>
                  {useReranker ? 'Retrieval + reranking' : 'Retrieval only'}
                </strong>
              </div>

              <label className="toggle-control" htmlFor="use-reranker">
                <span>
                  <strong>Use reranker</strong>
                  <small>CrossEncoder relevance pass</small>
                </span>
                <input
                  id="use-reranker"
                  type="checkbox"
                  checked={useReranker}
                  onChange={(event) => setUseReranker(event.target.checked)}
                  disabled={queryState.loading}
                />
                <span className="toggle-track" aria-hidden="true">
                  <span />
                </span>
              </label>
            </div>

            <div className="form-actions">
              <div className="query-selectors">
                <label className="select-control" htmlFor="top-k">
                  <span>Evidence chunks</span>
                  <select
                    id="top-k"
                    value={topK}
                    onChange={(event) => setTopK(event.target.value)}
                    disabled={queryState.loading}
                  >
                    {[3, 5, 7, 10].map((value) => (
                      <option key={value} value={value}>
                        Top {value}
                      </option>
                    ))}
                  </select>
                </label>

                <label className="select-control" htmlFor="rerank-pool">
                  <span>Rerank pool</span>
                  <select
                    id="rerank-pool"
                    value={rerankPool}
                    onChange={(event) => setRerankPool(event.target.value)}
                    disabled={queryState.loading || !useReranker}
                  >
                    {[10, 15, 20, 30, 40, 50].map((value) => (
                      <option key={value} value={value}>
                        Top {value}
                      </option>
                    ))}
                  </select>
                </label>
              </div>

              <button
                className="ask-button"
                type="submit"
                disabled={queryState.loading || question.trim().length < 3}
              >
                {queryState.loading ? (
                  <>
                    <span className="spinner" aria-hidden="true" />
                    Searching report
                  </>
                ) : (
                  <>
                    Ask PolicyDocIQ
                    <ArrowIcon />
                  </>
                )}
              </button>
            </div>
          </form>

          <div className="samples">
            <span className="samples-label">Try a sample question</span>
            <div className="sample-list">
              {SAMPLE_QUESTIONS.map((sample) => (
                <button
                  type="button"
                  key={sample}
                  onClick={() => {
                    setQuestion(sample)
                    setQueryState((current) => ({ ...current, error: '' }))
                  }}
                  disabled={queryState.loading}
                >
                  {sample}
                </button>
              ))}
            </div>
          </div>
        </section>

        {queryState.error && (
          <div className="notice error-notice query-error" role="alert">
            <strong>Query failed.</strong>
            <span>{queryState.error}</span>
          </div>
        )}

        {queryState.loading && (
          <section className="answer-card loading-card" aria-live="polite">
            <div className="loading-heading">
              <span className="spinner large" aria-hidden="true" />
              <div>
                <strong>Retrieving evidence</strong>
                <span>Searching the indexed report and composing an answer…</span>
              </div>
            </div>
            <div className="skeleton wide" />
            <div className="skeleton" />
            <div className="skeleton short" />
          </section>
        )}

        {result && !queryState.loading && (
          <section className="results" aria-live="polite">
            <article className="answer-card">
              <div className="answer-header">
                <div className="section-heading compact">
                  <span className="section-icon accent">
                    <SparkleIcon />
                  </span>
                  <div>
                    <span className="answer-kicker">Grounded response</span>
                    <h2>Answer</h2>
                  </div>
                </div>
                <div className="answer-actions">
                  <span className="evidence-count">
                    {result.evidence?.length ?? 0} evidence chunks
                  </span>
                  <button className="secondary-button" type="button" onClick={copyAnswer}>
                    <CopyIcon />
                    {copyState === 'copied'
                      ? 'Copied'
                      : copyState === 'error'
                        ? 'Copy failed'
                        : 'Copy answer'}
                  </button>
                  <button className="secondary-button" type="button" onClick={clearResult}>
                    Clear result
                  </button>
                </div>
              </div>

              <div className="answer-text">{result.answer}</div>

              <div className="citations">
                <span>Citations</span>
                {result.citations?.length > 0 ? (
                  result.citations.map((page, index) => (
                    <span className="citation-badge" key={`${page}-${index}`}>
                      Page {page}
                    </span>
                  ))
                ) : (
                  <span className="no-citations">No citations found</span>
                )}
              </div>
            </article>

            <div className="evidence-section">
              <div className="evidence-title">
                <div>
                  <h2>Retrieved evidence</h2>
                  <p>Source passages ranked by semantic relevance.</p>
                </div>
              </div>

              <div className="evidence-list">
                {(result.evidence ?? []).map((item, index) => {
                  const evidenceKey =
                    item.chunk_id || `${item.page_number}-${index}`

                  return (
                    <EvidenceCard
                      key={evidenceKey}
                      item={item}
                      index={index}
                      expanded={Boolean(expandedEvidence[evidenceKey])}
                      onToggle={() =>
                        setExpandedEvidence((current) => ({
                          ...current,
                          [evidenceKey]: !current[evidenceKey],
                        }))
                      }
                    />
                  )
                })}
              </div>
            </div>
          </section>
        )}

        <aside className="evaluation-note">
          <strong>Evaluation pipeline</strong>
          <span>
            Results are saved to <code>outputs/evaluation_results.csv</code> after
            running <code>python scripts/05_run_evaluation.py</code>.
          </span>
        </aside>
      </main>

      <footer>
        <span>PolicyDocIQ</span>
        <span>BGE-M3 embeddings · Qdrant retrieval · Evidence-based answers</span>
      </footer>
    </div>
  )
}

export default App
