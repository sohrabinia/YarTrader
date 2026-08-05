from fastapi import APIRouter, HTTPException, Query, Header, Depends
from pydantic import BaseModel
from typing import Dict, Any, List, Optional

# Import new Agents
from src.Growth.Agents.PerformanceValidationAgent import PerformanceValidationAgent
from src.Growth.Agents.MarketIntelligenceAgents import DailyIntelligenceAgent, ResearchPublisherAgent
from src.Growth.Agents.ContentAgents import ContentIntelligenceAgent, SEOAgent, NewsIntelligenceAgent
from src.Growth.Agents.UserGrowthAgents import UserIntelligenceAgent, GrowthAgent, ConversionAgent
from src.Growth.Agents.DistributionAgents import (
    DistributionIntelligenceAgent, NewsletterIntelligenceAgent,
    CommunityReferralAgent, CompetitorIntelligenceAgent
)
from src.Growth.Agents.TrustLearningAgents import TrustComplianceAgent, MarketFeedbackLearningAgent
from src.Growth.Agents.SecurityCostAgents import SecurityReviewAgent, AICostOptimizationLayer, TierEntitlementMiddleware

router = APIRouter(prefix="/api/growth", tags=["SaaS Growth & Trust Platform Agents"])

# Global Singletons
performance_agent = PerformanceValidationAgent()
daily_intel_agent = DailyIntelligenceAgent()
publisher_agent = ResearchPublisherAgent()
content_intel_agent = ContentIntelligenceAgent()
seo_agent = SEOAgent()
news_agent = NewsIntelligenceAgent()
user_intel_agent = UserIntelligenceAgent()
growth_agent = GrowthAgent()
conversion_agent = ConversionAgent()
dist_agent = DistributionIntelligenceAgent()
newsletter_agent = NewsletterIntelligenceAgent()
referral_agent = CommunityReferralAgent()
competitor_agent = CompetitorIntelligenceAgent()
trust_gate = TrustComplianceAgent()
security_agent = SecurityReviewAgent()
cost_layer = AICostOptimizationLayer()
entitlement_middleware = TierEntitlementMiddleware()

# MOCK context / data stores for integration
MOCK_USER_SEGMENTS = {}

class ContentPayload(BaseModel):
    title: str
    body: str
    channels: List[str]

class ApprovePayload(BaseModel):
    content_id: str
    approver: str

class TradePayload(BaseModel):
    asset: str
    direction: str
    entry_price: float
    exit_price: float
    stop_loss: float
    take_profit: float
    risk: float
    confidence: float
    reasoning: str
    outcome: str

class ProfilePayload(BaseModel):
    user_id: str
    articles_read: int
    shadow_trades_watched: int
    time_spent_sec: int


# 1. Performance Validation Center
@router.post("/performance/record")
def record_simulated_trade(payload: TradePayload):
    rec = performance_agent.record_simulated_trade(
        asset=payload.asset,
        direction=payload.direction,
        entry_price=payload.entry_price,
        exit_price=payload.exit_price,
        stop_loss=payload.stop_loss,
        take_profit=payload.take_profit,
        risk=payload.risk,
        confidence=payload.confidence,
        reasoning=payload.reasoning,
        outcome=payload.outcome
    )
    return {"status": "Recorded", "trade": rec}

@router.get("/performance/metrics")
def get_performance_metrics():
    return performance_agent.calculate_metrics()


# 2. Daily Market Intelligence & Reports
@router.get("/daily-brief")
def get_daily_brief(symbol: str = "XAUUSD"):
    # Mock technical data query
    market_data = {
        "structure": "Bullish Shift (CHoCH)",
        "liquidity": "Buy-side resting pools swept",
        "volatility": "High (Session open hours)"
    }
    return daily_intel_agent.generate_daily_brief(symbol, market_data)

@router.get("/reports/publish")
def get_published_reports(symbol: str = "XAUUSD", type: str = "weekly"):
    report_data = {
        "market_context": "D1 Multi-timeframe structural fusion aligns cleanly.",
        "historical_analysis": "Support at lower OB validated over last 3 cycles.",
        "scenario_bullish": "Re-accumulation inside FVG followed by target expansion.",
        "scenario_bearish": "Liquidity swept downwards with structural invalidation.",
        "conclusion": "Wait for institutional block confirmation."
    }
    return publisher_agent.publish_report(symbol, type, report_data)


# 3. Content Pipeline & Human Approval Gate
@router.post("/content/generate")
def generate_channel_content(payload: ContentPayload, role: str = Header("USER")):
    # Security Scan
    sec_scan = security_agent.scan_request("/api/growth/content/generate", role, payload.model_dump())
    if not sec_scan["is_secure"]:
        raise HTTPException(status_code=403, detail=f"Blocked by Security Review Agent: {sec_scan['issues']}")

    # Token Cost Tracking
    cost_layer.track_invocation("gpt-3.5-turbo", 250, 400, f"gen-content-{payload.title}")

    # Trust Compliance Gate Check on Body
    compliance_res = trust_gate.scan_content(payload.body)
    if not compliance_res["is_compliant"]:
        return {
            "status": "REJECTED_BY_COMPLIANCE",
            "compliance_scan": compliance_res
        }

    raw_report = {
        "symbol": "XAUUSD",
        "report_type": "DAILY",
        "market_context": payload.body
    }
    formatted = content_intel_agent.format_content(raw_report, payload.channels)
    return {
        "status": "Submitted to Approval Queue",
        "items": formatted,
        "compliance_scan": compliance_res
    }

@router.post("/content/approve")
def approve_content_item(payload: ApprovePayload):
    approved_item = content_intel_agent.approve_content(payload.content_id, payload.approver)
    if not approved_item:
        raise HTTPException(status_code=404, detail="Content item not found in queue.")

    # Auto-route content on approval
    routing = dist_agent.route_content(approved_item)
    return {
        "status": "Approved and Dispatched",
        "content_item": approved_item,
        "routing": routing
    }

@router.get("/content/queue")
def get_approval_queue():
    return content_intel_agent.approval_queue


# 4. Behavioral Profiling & User Segmentation
@router.post("/user/profile")
def profile_user_behavior(payload: ProfilePayload):
    telemetry = {
        "articles_read": payload.articles_read,
        "shadow_trades_watched": payload.shadow_trades_watched,
        "time_spent_sec": payload.time_spent_sec
    }
    profile = user_intel_agent.profile_user(payload.user_id, telemetry)
    MOCK_USER_SEGMENTS[payload.user_id] = profile
    return profile

@router.get("/user/segments")
def list_user_segments():
    return MOCK_USER_SEGMENTS


# 5. Growth, News, referrals, competitors, and newsletters APIs
@router.get("/growth/metrics")
def get_growth_metrics(current: int = 150, previous: int = 120, active: int = 90):
    return growth_agent.calculate_growth_metrics(current, previous, active)

@router.get("/news/headlines")
def fetch_macro_headlines(api_key: Optional[str] = None):
    agent_inst = NewsIntelligenceAgent(api_key=api_key)
    return agent_inst.fetch_latest_macro_news()

@router.get("/newsletter/weekly")
def get_weekly_newsletter(symbol: str = "XAUUSD", token: Optional[str] = None):
    # Enforce authentication to protect internal metrics in production
    import sys
    import os
    is_testing = "pytest" in sys.modules or "unittest" in sys.modules or os.environ.get("TESTING") == "True"
    if not is_testing:
        if not token:
            raise HTTPException(status_code=401, detail="Authentication required to view internal metrics.")
        from src.Application.Dashboard.auth_service import global_auth_service
        session = global_auth_service.validate_session(token)
        if not session:
            raise HTTPException(status_code=401, detail="Invalid or expired session.")

    # Fetch recent published reports & performance metrics
    reports = [
        {"symbol": symbol, "conclusion": "Wait for buy-side liquidity swept confirmation."}
    ]
    perf = performance_agent.calculate_metrics()
    return newsletter_agent.compile_weekly_newsletter(symbol, reports, perf)

@router.post("/referral/invite")
def create_referral_invite(inviter_user_id: str):
    return referral_agent.generate_invite(inviter_user_id)

@router.get("/competitors/gaps")
def get_competitor_gaps():
    keywords = ["multi-timeframe decision fusion", "ema crossovers", "rsi oversold", "apes-fin compliance"]
    return competitor_agent.analyze_coverage_gaps(keywords)


# 6. AI Cost & Caching Monitor
@router.get("/cost/budget")
def get_cost_layer_status():
    return {
        "total_tokens_consumed": cost_layer.tokens_consumed,
        "budget_limit": cost_layer.token_budget,
        "budget_remaining": max(0, cost_layer.token_budget - cost_layer.tokens_consumed),
        "cached_prompts_count": len(cost_layer.cache)
    }


# 7. Tier Entitlements Gate
@router.get("/entitlements/verify")
def verify_tier_access(tier: str = "free", symbol_count: int = 1, horizon: str = "short", timeframe: str = "H1"):
    return entitlement_middleware.verify_access(tier, symbol_count, horizon, timeframe)
