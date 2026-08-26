from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
from src.Risk.Services.prop_challenge_engine import prop_challenge_engine

router = APIRouter(prefix="/api/prop", tags=["Prop Challenge API"])

class PropConfigPayload(BaseModel):
    account_size: Optional[float] = 100000.0
    daily_loss_limit_percent: Optional[float] = 5.0
    max_drawdown_percent: Optional[float] = 10.0
    risk_per_trade_percent: Optional[float] = 1.0
    max_concurrent_positions: Optional[int] = 3
    session_rules: Optional[str] = "No holding through high-impact news or overnight session close."

@router.get("/challenge")
def get_prop_challenge():
    """Retrieves current Prop Challenge risk status and metrics."""
    return prop_challenge_engine.get_status()

@router.post("/config")
def configure_prop_challenge(payload: PropConfigPayload):
    """Configures Prop Challenge risk parameters."""
    try:
        data = payload.model_dump() if hasattr(payload, "model_dump") else payload.dict()
        return prop_challenge_engine.configure(data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
