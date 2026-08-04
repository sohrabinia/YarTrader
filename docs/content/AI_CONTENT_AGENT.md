# AI Content Agent — Phase P0 Production Implementation

## 1. Implementation Status
* **Status:** `IMPLEMENTED`

## 2. Production Code Architecture
* **File Paths:**
  * `src/Growth/ContentIntelligence/interfaces.py` (Abstract generator interface decoupling LLM providers)
  * `src/Growth/ContentIntelligence/providers.py` (Mock/Local and pluggable live production adapters)
  * `src/Application/Services/content_api_router.py` (FastAPI router endpoints)
* **Main Classes:**
  * `ContentIntelligenceInterface`: Base contract ensuring decoupled generation and metadata lineage traceability.
  * `MockProviderAdapter`: Offline, deterministic generation supporting both English (`en`) and Persian (`fa`) output briefs.
  * `ProductionLLMProviderAdapter`: Live LLM API connector designed to plug seamlessly in production without disrupting automated offline testing pipelines.
* **API Endpoints:**
  * `POST /api/content/drafts/generate`: API request to generate a structured content draft, carrying full traceability and language parameters.
  * `GET /api/content/drafts`: Queries draft registry with asset symbol and status filters.
  * `GET /api/content/drafts/{id}`: Detailed metadata retrieval containing source tracing metrics and Trust compliance log audits.

## 3. Data Flow sequence
```
[Research Source Intelligence Payload]
                 │
                 ▼ (Language: "fa" | "en")
[ContentIntelligenceInterface (Provider Decoupling)]
                 │
                 ▼
[MockProviderAdapter / ProductionLLMProviderAdapter]
                 │
                 ▼ (Retains 100% Lineage Tracking)
[Extensible TrustReviewEngine Compliance Pipeline]
```

## 4. Lineage & Source Traceability
Every draft generated and stored contains exact, auditable record maps backing up to the underlying quantitative intelligence feed:
- `source_intelligence_id`: Original research event reference.
- `symbols`: Specific list of underlying assets evaluated (e.g., `['XAUUSD', 'GOLD']`).
- `language`: Language used for drafting (`en` / `fa`).
- `created_at`: Exact timestamp marking creation date.
