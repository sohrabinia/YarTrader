import uuid
import re
import datetime
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel
from typing import Dict, Any, List, Optional

from src.Growth.ContentIntelligence.providers import MockProviderAdapter
from src.Growth.ContentIntelligence.trust_engine import TrustReviewEngine
from src.Growth.ContentIntelligence.repository import ContentRepository
from src.Content.Generators.ArticleGenerator import ArticleGenerator

router = APIRouter(prefix="/api/content", tags=["Content Intelligence & Articles"])

# Thread-safe global instances
repo = ContentRepository()
draft_provider = MockProviderAdapter()
article_provider = ArticleGenerator()
trust_engine = TrustReviewEngine()

# ==================================================
# PHASE P0 - Content Draft Schema Payloads & Endpoints
# ==================================================

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
    raw_draft = draft_provider.generate_draft({
        "source_intelligence_id": payload.source_intelligence_id,
        "symbols": payload.symbols,
        "title": payload.title,
        "body": payload.body,
        "format": payload.format
    }, language=payload.language)

    # Compliance review
    review_res = trust_engine.scan_draft(raw_draft)
    initial_status = review_res["status"]
    final_body = review_res["appended_body"]

    draft_id = f"draft-{uuid.uuid4().hex[:8]}"

    # Save to SQLite
    repo.create_draft(
        draft_id=draft_id,
        title=raw_draft["title"],
        body=final_body,
        format_type=raw_draft["format"],
        language=raw_draft["language"],
        status=initial_status,
        source_id=raw_draft["source_intelligence_id"],
        symbols=raw_draft["symbols"]
    )

    repo.save_review(
        content_id=draft_id,
        status=initial_status,
        violations=review_res["violations"],
        disclosures=review_res["disclosures"]
    )

    return {
        "status": "PROCESSED",
        "draft": repo.get_draft(draft_id)
    }


@router.get("/drafts")
def list_drafts(
    status: Optional[str] = Query(None, description="Filter by status"),
    symbol: Optional[str] = Query(None, description="Filter by asset symbol")
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
        raise HTTPException(status_code=404, detail=f"Content draft '{id}' not found.")
    return draft


# ==================================================
# PHASE P1 - Article Generation & Human Approval Queue
# ==================================================

class GenerateArticlePayload(BaseModel):
    source_intelligence_id: str
    symbols: List[str]
    timeframes: Optional[List[str]] = ["M15", "M5"]
    category: Optional[str] = "MARKET_RESEARCH" # MARKET_RESEARCH, EDUCATIONAL, SUMMARY
    sentiment: Optional[str] = "NEUTRAL"
    risk_level: Optional[str] = "LOW"
    language: Optional[str] = "en"
    title: Optional[str] = "Comprehensive Analysis"

    # Textual data variables
    market_context: Optional[str] = "Lateral range structure verified inside NYC session FVG bounds."
    technical_analysis: Optional[str] = "Bullish swing confirmation with high order block velocity."
    fundamental_context: Optional[str] = "Awaiting macro interest rate announcement metrics."
    regime_analysis: Optional[str] = "Accumulation phase consolidation."
    risk_factors: Optional[str] = "Invalidation if H1 swing breaks down."

    concept_explanation: Optional[str] = "Multi-timeframe structures align direction with execution timing."
    pattern_behavior: Optional[str] = "FVGs provide high-probability support reaction areas."
    learning_insights: Optional[str] = "Filtering with higher timeframe trend decreases noise."

    observations: Optional[str] = "High tick accumulation observed."
    risks: Optional[str] = "Breach of baseline setup triggers stop loss."

@router.post("/articles/generate")
def generate_article(payload: GenerateArticlePayload):
    """
    Generates a structured Article (Market Research, Educational, or Summary) from research data.
    Automatically routes the generated article to the TrustReviewEngine compliance gate.
    If compliant, sets state to PENDING_REVIEW; if violation exists, sets state to REJECTED.
    """
    # 1. Generate multi-dimensional Article via decoupled ArticleGenerator
    raw_article = article_provider.generate_draft(payload.model_dump(), language=payload.language)

    # 2. Hard synchronous TrustReview compliance scan
    review_res = trust_engine.scan_draft(raw_article)
    compliance_status = review_res["status"]

    # Map compliance to Article workflow states
    # If COMPLIANT -> PENDING_REVIEW, else REJECTED
    final_status = "PENDING_REVIEW" if compliance_status in ["APPROVED", "FLAGGED"] else "REJECTED"
    final_body = review_res["appended_body"]

    article_id = f"art-{uuid.uuid4().hex[:8]}"

    # Convert titles and paragraphs into sanitized html
    html_body = raw_article["html"]
    # Appended disclaimers if compliant
    if final_status != "REJECTED" and review_res["disclosures"]:
        disclaimer_html = "<br><br>---<br>" + "<br>".join(review_res["disclosures"])
        html_body += disclaimer_html

    # 3. Store Article Draft in isolated ContentArticle database tables
    repo.create_article(
        article_id=article_id,
        title=raw_article["title"],
        body=final_body,
        html=html_body,
        format_type=raw_article["format"],
        language=raw_article["language"],
        status=final_status,
        version="v1.0",
        category=raw_article["metadata"]["category"],
        symbols=raw_article["symbols"],
        timeframes=raw_article["metadata"]["timeframes"],
        sentiment=raw_article["metadata"]["sentiment"],
        risk_level=raw_article["metadata"]["risk_level"],
        source_intelligence_id=raw_article["source_intelligence_id"]
    )

    # Store related trust logs in ContentReview
    repo.save_review(
        content_id=article_id,
        status=compliance_status,
        violations=review_res["violations"],
        disclosures=review_res["disclosures"]
    )

    # Record initial creation audit log
    repo.record_audit(
        article_id=article_id,
        previous_state="DRAFT",
        new_state=final_status,
        actor_id="SYSTEM_GENERATOR",
        comment=f"Article successfully synthesized from intelligence source {raw_article['source_intelligence_id']}. Compliance status: {compliance_status}."
    )

    return {
        "status": "ARTICLE_GENERATED",
        "article": repo.get_article(article_id)
    }


@router.get("/articles/pending")
def list_pending_approval_queue():
    """
    Lists Articles currently residing inside the human approval review queue (status: PENDING_REVIEW).
    """
    return repo.list_articles(status="PENDING_REVIEW")


@router.get("/articles/{id}")
def get_article_details(id: str):
    """
    Retrieves full details of an Article, including markdown body, HTML representation,
    source metadata lineage, Trust review audit logs, and status versioning histories.
    """
    article = repo.get_article(id)
    if not article:
        raise HTTPException(status_code=404, detail=f"Article draft with ID '{id}' not found.")
    return article


class ReviewPayload(BaseModel):
    action: str # APPROVE, REJECT, REQUEST_REVISION
    actor_id: str
    comment: Optional[str] = ""

@router.post("/articles/{id}/review")
def review_article(id: str, payload: ReviewPayload):
    """
    Processes human intervention review actions (APPROVE, REJECT, REQUEST_REVISION).
    Transitions workflow states and appends comprehensive audit trails.
    """
    article = repo.get_article(id)
    if not article:
        raise HTTPException(status_code=404, detail=f"Article draft with ID '{id}' not found.")

    previous_state = article["status"]
    action_upper = payload.action.upper()

    # Determine next state
    if action_upper == "APPROVE":
        new_state = "APPROVED"
        comment = payload.comment or "Article approved by administrator review gate."
    elif action_upper == "REJECT":
        new_state = "REJECTED"
        comment = payload.comment or "Article rejected and archived."
    elif action_upper == "REQUEST_REVISION":
        new_state = "NEEDS_REVISION"
        comment = payload.comment or "Revision requested for draft improvements."
    else:
        raise HTTPException(status_code=400, detail=f"Invalid review action '{payload.action}'. Supported values are: APPROVE, REJECT, REQUEST_REVISION.")

    # Apply state transitions and record audit log
    audit_rec = repo.record_audit(
        article_id=id,
        previous_state=previous_state,
        new_state=new_state,
        actor_id=payload.actor_id,
        comment=comment
    )

    # If approved, move to final transition PUBLISH_READY automatically or sequentially
    if new_state == "APPROVED":
        repo.record_audit(
            article_id=id,
            previous_state="APPROVED",
            new_state="PUBLISH_READY",
            actor_id="SYSTEM_PIPELINE",
            comment="Approved draft transitioned automatically to publication ready."
        )

    return {
        "status": "REVIEW_PROCESSED",
        "action_taken": action_upper,
        "article": repo.get_article(id)
    }


class EditArticlePayload(BaseModel):
    title: str
    body: str
    actor_id: str
    comment: Optional[str] = "Human manual edits saved."

@router.put("/articles/{id}/edit")
def edit_article(id: str, payload: EditArticlePayload):
    """
    Saves human edits directly on draft contents, triggers a clean auto-version increment
    (e.g., v1.0 -> v1.1), reruns compliance filters, and updates audit records.
    """
    article = repo.get_article(id)
    if not article:
        raise HTTPException(status_code=404, detail=f"Article draft with ID '{id}' not found.")

    previous_state = article["status"]
    current_version = article["version"]

    # Parse and safely increment version number (vX.Y -> Y + 1)
    match = re.match(r"v(\d+)\.(\d+)", current_version)
    if match:
        major = int(match.group(1))
        minor = int(match.group(2))
        new_version = f"v{major}.{minor + 1}"
    else:
        new_version = "v1.1"

    # Rerun TrustReview on modified text draft
    temp_draft = {
        "title": payload.title,
        "body": payload.body,
        "language": article["language"],
        "source_intelligence_id": article["source_intelligence_id"]
    }
    review_res = trust_engine.scan_draft(temp_draft)
    compliance_status = review_res["status"]

    # Reset state to PENDING_REVIEW if compliant, otherwise keep REJECTED
    new_state = "PENDING_REVIEW" if compliance_status in ["APPROVED", "FLAGGED"] else "REJECTED"
    final_body = review_res["appended_body"]

    # Generate updated HTML
    html_body = payload.body
    html_body = re.sub(r"# (.*)", r"<h1>\1</h1>", html_body)
    html_body = re.sub(r"## (.*)", r"<h2>\1</h2>", html_body)
    html_body = html_body.replace("\n", "<br>")
    if new_state != "REJECTED" and review_res["disclosures"]:
        disclaimer_html = "<br><br>---<br>" + "<br>".join(review_res["disclosures"])
        html_body += disclaimer_html

    # Save updates inside database
    repo.update_article(
        article_id=id,
        title=payload.title,
        body=final_body,
        html=html_body,
        status=new_state,
        version=new_version
    )

    # Update related ContentReview logs
    repo.save_review(
        content_id=id,
        status=compliance_status,
        violations=review_res["violations"],
        disclosures=review_res["disclosures"]
    )

    # Record edit change audit history
    repo.record_audit(
        article_id=id,
        previous_state=previous_state,
        new_state=new_state,
        actor_id=payload.actor_id,
        comment=f"Manual content modifications applied. Version incremented to {new_version}. Compliance review result: {compliance_status}. Comment: {payload.comment}"
    )

    return {
        "status": "ARTICLE_UPDATED",
        "new_version": new_version,
        "compliance_status": compliance_status,
        "article": repo.get_article(id)
    }
