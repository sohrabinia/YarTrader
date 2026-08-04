import uuid
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel
from typing import Dict, Any, List, Optional

from src.Growth.ContentIntelligence.providers import MockProviderAdapter
from src.Growth.ContentIntelligence.trust_engine import TrustReviewEngine
from src.Growth.ContentIntelligence.repository import ContentRepository

router = APIRouter(prefix="/api/content", tags=["Content Intelligence P0"])

# Thread-safe global instances
repo = ContentRepository()
provider = MockProviderAdapter()
trust_engine = TrustReviewEngine()

class GenerateDraftPayload(BaseModel):
    source_intelligence_id: str
    symbols: List[str]
    title: str
    body: str
    format: Optional[str] = "ARTICLE"
    language: Optional[str] = "en"

@router.post("/drafts/generate")
def generate_draft(payload: GenerateDraftPayload):
    """
    Triggers dynamic draft creation from underlying research intelligence payloads.
    Supports English ("en") and Persian ("fa") output generation with trace mappings.
    Runs full Trust & Compliance rule reviews, blocking or flagging unsafe claims.
    """
    # 1. Decoupled Provider Generation (Passes 100% trace mapping metadata)
    raw_draft = provider.generate_draft({
        "source_intelligence_id": payload.source_intelligence_id,
        "symbols": payload.symbols,
        "title": payload.title,
        "body": payload.body,
        "format": payload.format
    }, language=payload.language)

    # 2. Extensible Trust & Compliance review chain
    review_res = trust_engine.scan_draft(raw_draft)

    # Determine initial database status
    initial_status = review_res["status"]

    # Use the compliance appended body text
    final_body = review_res["appended_body"]

    draft_id = f"draft-{uuid.uuid4().hex[:8]}"

    # 3. Secure isolated database storage insertion
    stored = repo.create_draft(
        draft_id=draft_id,
        title=raw_draft["title"],
        body=final_body,
        format_type=raw_draft["format"],
        language=raw_draft["language"],
        status=initial_status,
        source_id=raw_draft["source_intelligence_id"],
        symbols=raw_draft["symbols"]
    )

    # Save Trust review audit logs
    repo.save_review(
        content_id=draft_id,
        status=initial_status,
        violations=review_res["violations"],
        disclosures=review_res["disclosures"]
    )

    # Fetch fresh metadata with nested references
    full_draft = repo.get_draft(draft_id)
    return {
        "status": "PROCESSED",
        "draft": full_draft
    }


@router.get("/drafts")
def list_drafts(
    status: Optional[str] = Query(None, description="Filter by status (APPROVED, REJECTED, FLAGGED)"),
    symbol: Optional[str] = Query(None, description="Filter by underlying asset symbol (e.g., XAUUSD)")
):
    """
    Lists stored content drafts from isolated SQL database with symbol and status filters.
    """
    return repo.list_drafts(status=status, symbol=symbol)


@router.get("/drafts/{id}")
def get_draft_by_id(id: str):
    """
    Retrieves detailed content draft data, lineage traceability matrix, and Trust audit logs.
    """
    draft = repo.get_draft(id)
    if not draft:
        raise HTTPException(status_code=404, detail=f"Content draft with ID '{id}' not found.")
    return draft
