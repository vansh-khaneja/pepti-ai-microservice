# Pepti Wiki AI — Current Implementation (PostgreSQL + Qdrant)

This document describes only what is implemented today. It focuses on the live data stores (PostgreSQL and Qdrant), the workflows, endpoints, and logic currently in use.

- Runtime: FastAPI (Python)
- Vector DB: Qdrant Cloud (cosine similarity)
- RDBMS: PostgreSQL (external/managed)
- LLM/Embeddings: OpenAI (GPT‑4o‑mini, text‑embedding‑3‑small)
- Web Search: SerpAPI + scraping (BeautifulSoup)
- Config: Pydantic Settings + .env

---

## 1) Chat Conversations (What exists today)

We do not persist full chat transcripts yet. Responses are generated on demand using:
- Qdrant (vector similarity) for peptide context
- Web search + chunk embeddings for additional context when needed
- Chat restrictions pulled from PostgreSQL and injected into prompts
- Endpoint usage analytics stored in PostgreSQL

Metrics returned to the client are included in API responses where relevant (e.g., similarity scores). Internal timing and usage are tracked by the analytics middleware.

Technologies used today for this area:
- Qdrant (searching peptide vectors)
- PostgreSQL (analytics + restrictions + allowed URLs)
- OpenAI (LLM + embeddings)

---

## 2) Generating New Peptide Info (Implemented)

### 2.1 Storage (Qdrant)
Peptides are stored in Qdrant as vectors with payload fields (name, overview, mechanism_of_actions, potential_research_fields, text_content). The collection uses cosine similarity and a vector size of 768 (embeddings from OpenAI are truncated to this size).

### 2.2 Retrieval Logic
- General search:
  1) Generate embedding for the user query
  2) Vector similarity search in Qdrant
  3) Take the best match and return its payload + similarity score
- Specific peptide query:
  1) Fetch by name (using the name index/payload)
  2) Return canonical payload

### 2.3 Technologies
- Qdrant Cloud (Distance.COSINE)
- OpenAI text‑embedding‑3‑small (truncated to 768 dims)
- FastAPI services under `app/services/peptide_service.py` and `app/services/qdrant_service.py`

---

## 2.4) Advanced Peptide Info Generation (NEW - Tavily-First Approach)

### 2.4.1 Overview
A new advanced peptide information generation system that uses a Tavily-first approach with SerpAPI fallback, similar to the chat system but optimized for comprehensive peptide research.

### 2.4.2 Workflow
1. **Tavily Search First**: Query Tavily API for quick, accurate results
2. **Accuracy Assessment**: Check if Tavily results meet accuracy threshold (0.8)
3. **LLM Tuning**: If accuracy is good, tune results with LLM for comprehensive response
4. **SerpAPI Fallback**: If accuracy is poor, fall back to existing SerpAPI + scraping approach
5. **Database Persistence**: Save all data including source content, URLs, and metadata

### 2.4.3 Database Schema
- **PeptideInfoSession**: Stores session metadata (peptide_name, requirements, user_id)
- **PeptideInfoMessage**: Stores individual messages with source tracking and accuracy scores

### 2.4.4 API Endpoints
- `POST /api/v1/peptide-info/generate`: Generate comprehensive peptide information
- `GET /api/v1/peptide-info/sessions/{session_id}`: Get session history
- `GET /api/v1/peptide-info/sessions`: List all sessions

### 2.4.5 Technologies
- Tavily API (primary search)
- SerpAPI + BeautifulSoup (fallback)
- OpenAI GPT-4o-mini (LLM tuning)
- PostgreSQL (session and message storage)
- FastAPI services under `app/services/peptide_info_service.py`

---

## 3) Chat Restrictions (Implemented)

Rules are stored in PostgreSQL and pulled at runtime to constrain the LLM response.

- Examples enforced:
  - No medical advice/dosage
  - Avoid illegal/controlled substance guidance
  - Encourage professional consultation for personal cases

PostgreSQL table (present in codebase):
```sql
CREATE TABLE chat_restrictions (
  id SERIAL PRIMARY KEY,
  restriction_text TEXT UNIQUE NOT NULL
);
```

Endpoints (implemented under `app/api/v1/endpoints/chat_restrictions.py`):
- POST add restriction
- GET list restrictions
- DELETE restriction by text

---

## 4) Specific URLs (Allowed Domains) & Web Search Flow (Implemented)

### 4.1 Web Search Workflow
- Input: `peptide_name` + `requirements` → combined query (e.g., "BPC 157 Uses")
- SerpAPI call to fetch top results
- Filter results against the admin‑managed allowlist in PostgreSQL (only allowed domains are used)
- Scrape each allowed URL and extract title/content (BeautifulSoup)
- Chunk content to fixed size with overlap (currently ~1000 chars, overlap ~200, max ~5 chunks per site)
- Generate embeddings for the query and each chunk; compute cosine similarity
- Rank chunks, group by parent URL, use the best similarity per URL
- Optionally filter by confidence threshold (setting in config)
- Generate LLM answer using top chunks as context; return sources with similarity scores (6‑decimal precision)

### 4.2 Allowed URLs (PostgreSQL schema present)
```sql
CREATE TABLE allowed_urls (
  id SERIAL PRIMARY KEY,
  url TEXT UNIQUE NOT NULL,
  description TEXT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

Endpoints (implemented under `app/api/v1/endpoints/allowed_urls.py`):
- POST create allowed URL
- GET list allowed URLs
- DELETE allowed URL by id

---

## 5) AI Dashboard (Analytics & Control Panel) — Implemented Parts

- Analytics middleware stores endpoint usage in PostgreSQL
- Analytics endpoints expose daily/weekly/monthly aggregates

Endpoints (implemented under `app/api/v1/endpoints/analytics.py`):
- GET `/api/v1/analytics/daily?days=7`
- GET `/api/v1/analytics/weekly?weeks=4`
- GET `/api/v1/analytics/monthly?months=6`

These show counts and time‑bucketed usage pulled from the analytics tables.

---

## 6) Technologies & Settings Used Today

- FastAPI application entry: `app/main.py`
- Core config: `app/core/config.py` (env‑driven; includes QDRANT_URL/API key, DB URL, CONFIDENCE_SCORE, etc.)
- PostgreSQL usage today:
  - `chat_restrictions`
  - `allowed_urls`
  - analytics tables for endpoint usage
- Qdrant usage today:
  - `peptides` collection (cosine distance, vector size 768)
  - Payload includes peptide canonical fields + `text_content`
- OpenAI:
  - `text-embedding-3-small` for embeddings (truncated)
  - `gpt-4o-mini` for response generation
- SerpAPI + BeautifulSoup for web search & scraping

---

## 7) Request/Response Highlights (Current)

- Similarity scores are returned as floating‑point values with 6 decimal places
- Confidence threshold (percentage) is used to filter chunks (configurable via `CONFIDENCE_SCORE`)
- Sources are returned as a list of `{title, url, similarity_score, content_length}` grouped by parent URL

Example web search response (abridged):
```json
{
  "peptide_name": "BPC-157",
  "requirements": "Uses",
  "generated_response": "...",
  "source_sites": [
    {"title": "MedlinePlus", "url": "https://...", "similarity_score": 0.842361, "content_length": 9500}
  ],
  "search_timestamp": "2025-09-15T20:00:13Z"
}
```

---

## 9) Caching Workflow (per diagram)

This section documents the caching flow requested in the design diagram. It describes how the system should route a user query through caches, database/vector search, and external search before generating an answer with the LLM. This is an additive design note alongside the current implementation.

### 9.1 Flow Summary
1. User query arrives
2. Check Level‑1 cache (in‑memory):
   - If hit → return cached payload to LLM → apply chat restrictions → respond
   - If miss → proceed to DB/vector search
3. DB/vector search (Qdrant peptide similarity):
   - If similarity ≥ threshold → use this result → LLM → chat restrictions → respond
   - If similarity < threshold → proceed to Level‑2 cache
4. Check Level‑2 cache (e.g., Tavily/secondary store):
   - If hit → use cached payload → LLM → chat restrictions → respond
   - If miss → run Tavily/external search
5. Tavily/external search → gather context → LLM → apply chat restrictions → respond

---

## 10) Workflows (point‑wise)

- General peptide search (current)
  - Receive user query
  - Generate embedding (OpenAI)
  - Qdrant vector similarity search (cosine)
  - Return best peptide payload + similarity score
  - Generate LLM response with peptide context

- Peptide‑specific query (current)
  - Extract peptide name from path
  - Fetch peptide by name (Qdrant payload)
  - Return canonical fields (overview, mechanisms, research fields)
  - Generate LLM response with canonical context

- Web search + chunking (current)
  - Build query from `peptide_name + requirements`
  - SerpAPI → top results
  - Filter by allowed URLs (PostgreSQL)
  - Scrape title/content → split into chunks (≈1000 chars, 200 overlap, ≤5/site)
  - Embed query + chunks → cosine similarity per chunk
  - Rank and group by parent URL → best similarity per site
  - Filter by confidence threshold (config)
  - LLM response using top chunks; return sources with scores

- Chat restrictions (current)
  - Load restrictions from PostgreSQL
  - Inject into system prompt
  - Enforce safety rules in responses (no medical advice, etc.)

- Analytics (current)
  - Middleware logs endpoint usage to PostgreSQL
  - Daily/weekly/monthly aggregates exposed via analytics endpoints

- Caching (design per diagram)
  - Check L1 cache → hit returns directly to LLM
  - Miss → DB/vector search → if above threshold return, else check L2
  - L2 hit → return; L2 miss → Tavily/external search
  - Final result always passes through chat restrictions then LLM response

- Advanced peptide info generation (NEW)
  - Receive peptide name + requirements
  - Create PeptideInfoSession in PostgreSQL
  - Tavily search → get results + accuracy scores
  - If accuracy ≥ 0.8 → LLM tune → save to database → respond
  - If accuracy < 0.8 → SerpAPI fallback → scrape + chunk → LLM → save → respond
  - Store all data: source content, URLs, accuracy scores, metadata
