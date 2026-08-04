# Article Workflow Engine & Publishing Pipeline — Phase P1 Implementation

## 1. Implementation Status
* **Status:** `IMPLEMENTED`

## 2. Production Code Architecture
* **File Paths:**
  * `src/Growth/ContentIntelligence/database.py` (SQL schemas)
  * `src/Growth/ContentIntelligence/repository.py` (Draft updates, audits, and versions)
  * `src/Application/Services/content_api_router.py` (Endpoints under `/api/content/articles/`)

---

## 3. Workflow States Lifecycle Sequence

```
[Research Data Ingestion]
           │
           ▼
[ArticleGenerator Synthesis]
           │
           ▼ (Runs TrustReviewEngine compliance scanning)
           ├─────────────────────────┐
           ▼ (If Compliant)          ▼ (If Non-compliant)
   [PENDING_REVIEW]             [REJECTED]
           │
           ├─► [Action: REQUEST_REVISION] ──► [NEEDS_REVISION]
           │                                        │
           │                            [Action: Save human edits] ◄─┘
           │                                        │ (Increments version, e.g. v1.0 -> v1.1)
           │                                        ▼
           │                               [PENDING_REVIEW]
           │
           ├─► [Action: APPROVE] ──► [APPROVED] ──► [PUBLISH_READY]
```

* **`DRAFT` / `TRUST_PENDING`**: Original generation pipeline start.
* **`PENDING_REVIEW`**: Compliant articles awaiting human audit.
* **`REJECTED`**: Articles flagged by compliance rules.
* **`NEEDS_REVISION`**: Administrators request structural updates.
* **`APPROVED` / `PUBLISH_READY`**: Validated and cleared articles ready for distribution.

---

## 4. Multi-Versioning Schema
When an article is modified via `PUT /api/content/articles/{id}/edit`, the repository automatically parses and increments the version sequence:
- Initial state: `v1.0`
- Manual edit 1: `v1.1`
- Manual edit 2: `v1.2`
This ensures all modifications are tracked cleanly without data corruption.

---

## 5. Audit Log Record Format
All status transitions and comments are recorded inside the SQLite `ArticleAuditRecord` table:
* `id`: Unique audit identifier.
* `article_id`: Target article draft.
* `previous_state`: Status prior to change.
* `new_state`: Status after transition.
* `actor_id`: Username or SRE system id of the transitioning actor.
* `comment`: Revision notes or approval details.
* `timestamp`: Precise date/time logs.
