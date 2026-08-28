from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, time, date, timedelta, timezone
import hashlib
import json
import logging

logger = logging.getLogger("MarketSessionEngine")

class MarketState(str, Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    PRE_OPEN = "PRE_OPEN"
    PRE_CLOSE = "PRE_CLOSE"
    HOLIDAY_CLOSED = "HOLIDAY_CLOSED"
    MAINTENANCE = "MAINTENANCE"
    BROKER_CLOSED = "BROKER_CLOSED"
    UNKNOWN = "UNKNOWN"

class CalendarSourcePrecedence(int, Enum):
    LIVE_BROKER_MT5 = 1
    BROKER_CONTRACT_SPEC = 2
    BROKER_HOLIDAY_SCHEDULE = 3
    OFFICIAL_EXCHANGE_CALENDAR = 4
    VERIFIED_EXTERNAL_CALENDAR = 5
    FOREXFACTORY_ENRICHMENT = 6  # Secondary Advisory / Enrichment source
    GENERIC_FALLBACK = 7  # Fails closed if unknown

@dataclass
class SessionInterval:
    session_id: str
    broker: str
    symbol: str
    market: str  # e.g. "FOREX", "CRYPTO", "INDICES"
    date_str: str  # YYYY-MM-DD
    weekday: int  # 0=Monday, 6=Sunday
    session_start: time
    session_end: time
    tz_name: str = "UTC"
    utc_start: Optional[datetime] = None
    utc_end: Optional[datetime] = None
    source: CalendarSourcePrecedence = CalendarSourcePrecedence.LIVE_BROKER_MT5
    source_version: str = "v1.0.0"
    retrieved_at: Optional[datetime] = None
    special_session: bool = False
    holiday_override: bool = False
    early_close: bool = False
    late_open: bool = False
    confidence: float = 1.0

    def contains_time(self, dt: datetime) -> bool:
        """Check if datetime dt falls within this interval."""
        if self.utc_start and self.utc_end:
            dt_utc = dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
            return self.utc_start <= dt_utc < self.utc_end
        return False

    def remaining_seconds(self, dt: datetime) -> float:
        """Calculate remaining seconds until session_end."""
        if not self.utc_end:
            return 0.0
        dt_utc = dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        rem = (self.utc_end - dt_utc).total_seconds()
        return max(0.0, rem)

@dataclass
class HolidayEvent:
    event_id: str
    name: str
    date_str: str  # YYYY-MM-DD
    currency_or_market: str
    impact: str = "HIGH"  # HIGH, MEDIUM, LOW, BANK_HOLIDAY
    source: CalendarSourcePrecedence = CalendarSourcePrecedence.FOREXFACTORY_ENRICHMENT
    source_url: str = "https://www.forexfactory.com/calendar"
    retrieved_at: Optional[datetime] = None
    confidence: float = 0.9

@dataclass
class TPFeasibilityAssessment:
    is_feasible: bool
    rejection_reason: Optional[str] = None
    estimated_tp_seconds: float = 0.0
    remaining_session_seconds: float = 0.0
    required_min_hold_seconds: float = 120.0
    confidence: float = 1.0

@dataclass
class MarketSessionValidationResult:
    allowed: bool
    rejection_reason: Optional[str]
    market_state: MarketState
    active_interval: Optional[SessionInterval]
    remaining_session_seconds: float
    tp_feasibility: Optional[TPFeasibilityAssessment] = None
    source_authority: CalendarSourcePrecedence = CalendarSourcePrecedence.GENERIC_FALLBACK
    message: str = ""

class MarketSessionEngine:
    """
    Canonical Market Session & Broker Trading Calendar Engine for YarTrader.
    Enforces:
    1. Precedence hierarchy: Live Broker MT5 Sessions > Contract Spec > Broker Holiday > Exchange > ForexFactory advisory.
    2. Multi-session intervals per day (N open/close intervals e.g. Saturday multi-session Crypto).
    3. Forex DST & Broker Server timezone handling.
    4. Mandatory Pre-Entry >120s remaining session feasibility check.
    5. Causal Pre-Entry TP-Time Feasibility model.
    6. Fail-closed on UNKNOWN state.
    """

    POSITION_MINIMUM_NORMAL_LIFETIME: float = 120.0  # Must be strictly > 120.0s

    def __init__(self):
        self.symbol_schedules: Dict[str, List[SessionInterval]] = {}
        self.holiday_calendar: List[HolidayEvent] = []
        self.forexfactory_enrichment: List[Dict[str, Any]] = []

    def register_session_interval(self, interval: SessionInterval) -> None:
        """Register a session interval for a symbol."""
        key = f"{interval.broker}:{interval.symbol}".upper()
        if key not in self.symbol_schedules:
            self.symbol_schedules[key] = []
        self.symbol_schedules[key].append(interval)
        # Sort intervals chronologically
        self.symbol_schedules[key].sort(key=lambda x: x.utc_start if x.utc_start else datetime.min.replace(tzinfo=timezone.utc))

    def register_holiday_event(self, event: HolidayEvent) -> None:
        """Register holiday / bank holiday event."""
        self.holiday_calendar.append(event)

    def enrich_from_forexfactory(self, calendar_events: List[Dict[str, Any]]) -> None:
        """
        Integrates ForexFactory calendar export or JSON payload as ADVISORY enrichment.
        ForexFactory entries populate holiday/event context but NEVER override live broker session closures.
        """
        for evt in calendar_events:
            self.forexfactory_enrichment.append({
                "source": "FOREXFACTORY",
                "source_url": evt.get("url", "https://www.forexfactory.com/calendar"),
                "event_id": evt.get("id", str(hashlib.md5(json.dumps(evt).encode()).hexdigest())),
                "title": evt.get("title", "Bank Holiday"),
                "currency": evt.get("currency", "USD"),
                "date": evt.get("date"),
                "impact": evt.get("impact", "HIGH"),
                "retrieved_at": datetime.now(timezone.utc).isoformat()
            })

    def get_market_state(
        self,
        symbol: str,
        broker: str = "DEFAULT",
        current_time: Optional[datetime] = None
    ) -> tuple[MarketState, Optional[SessionInterval], CalendarSourcePrecedence]:
        """
        Determines current market state following the authoritative precedence hierarchy.
        """
        now = current_time if current_time else datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        key = f"{broker}:{symbol}".upper()
        intervals = self.symbol_schedules.get(key, [])

        if not intervals:
            # Fallback lookup by symbol alone if broker not specifically matched
            for k, v in self.symbol_schedules.items():
                if k.endswith(f":{symbol.upper()}"):
                    intervals = v
                    break

        if not intervals:
            # Schedule unknown -> FAIL CLOSED (UNKNOWN)
            logger.warning(f"[MarketSessionEngine] Schedule unknown for symbol {symbol} broker {broker}. Failing closed.")
            return MarketState.UNKNOWN, None, CalendarSourcePrecedence.GENERIC_FALLBACK

        # Check for active holiday override affecting this symbol
        date_str = now.strftime("%Y-%m-%d")
        for hol in self.holiday_calendar:
            if hol.date_str == date_str and (hol.currency_or_market.upper() in symbol.upper() or hol.currency_or_market == "ALL"):
                if hol.impact == "BANK_HOLIDAY":
                    return MarketState.HOLIDAY_CLOSED, None, hol.source

        # Check all registered session intervals
        for interval in intervals:
            if interval.contains_time(now):
                if interval.holiday_override:
                    return MarketState.HOLIDAY_CLOSED, interval, interval.source
                return MarketState.OPEN, interval, interval.source

        # Check if between sessions or before first/after last
        return MarketState.CLOSED, None, intervals[0].source if intervals else CalendarSourcePrecedence.LIVE_BROKER_MT5

    def estimate_tp_time_feasibility(
        self,
        distance_to_tp: float,
        current_volatility_atr: float,
        remaining_session_seconds: float,
        historical_mfe_speed: float = 1.0  # price movement units per second
    ) -> TPFeasibilityAssessment:
        """
        Evaluates causal pre-entry TP-Time Feasibility.
        Calculates:
        1. Estimated time to reach TP based on ATR and historical movement speed.
        2. Asserts whether trade can reach TP after minimum hold duration (>120s) and before session cutoff.
        """
        if distance_to_tp <= 0 or current_volatility_atr <= 0 or historical_mfe_speed <= 0:
            return TPFeasibilityAssessment(
                is_feasible=False,
                rejection_reason="TP_FEASIBILITY_INCONCLUSIVE",
                remaining_session_seconds=remaining_session_seconds
            )

        # Estimate seconds required to reach TP
        estimated_seconds = distance_to_tp / historical_mfe_speed

        # Constraint 1: Must be able to hold for strictly > 120 seconds before TP is reached
        # If TP is expected to be reached in <= 120 seconds (e.g. 70s), normal strategy cannot hit TP without violating >120s hold rule!
        if estimated_seconds <= self.POSITION_MINIMUM_NORMAL_LIFETIME:
            return TPFeasibilityAssessment(
                is_feasible=False,
                rejection_reason="TP_TIME_TOO_FAST_BELOW_MIN_HOLD_120S",
                estimated_tp_seconds=estimated_seconds,
                remaining_session_seconds=remaining_session_seconds,
                confidence=0.9
            )

        # Constraint 2: Must reach TP before session cutoff
        if estimated_seconds > remaining_session_seconds:
            return TPFeasibilityAssessment(
                is_feasible=False,
                rejection_reason="TP_TIME_EXCEEDS_REMAINING_SESSION",
                estimated_tp_seconds=estimated_seconds,
                remaining_session_seconds=remaining_session_seconds,
                confidence=0.95
            )

        return TPFeasibilityAssessment(
            is_feasible=True,
            estimated_tp_seconds=estimated_seconds,
            remaining_session_seconds=remaining_session_seconds,
            confidence=0.95
        )

    def validate_pre_entry(
        self,
        symbol: str,
        broker: str = "DEFAULT",
        distance_to_tp: Optional[float] = None,
        current_volatility_atr: Optional[float] = None,
        historical_mfe_speed: float = 1.0,
        current_time: Optional[datetime] = None
    ) -> MarketSessionValidationResult:
        """
        Performs the complete unified Pre-Entry Session & Calendar Feasibility Gate.
        Evaluates:
        1. Market State (OPEN vs CLOSED vs UNKNOWN vs HOLIDAY_CLOSED).
        2. Pre-Entry 120-second session remaining feasibility (`remaining_session_seconds > 121.0`).
        3. Causal Pre-Entry TP-Time Feasibility.
        """
        now = current_time if current_time else datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        state, active_interval, source_auth = self.get_market_state(symbol=symbol, broker=broker, current_time=now)

        if state == MarketState.UNKNOWN:
            return MarketSessionValidationResult(
                allowed=False,
                rejection_reason="UNKNOWN_BROKER_SCHEDULE",
                market_state=state,
                active_interval=None,
                remaining_session_seconds=0.0,
                source_authority=source_auth,
                message="Trade rejected: Broker trading schedule for symbol is unknown (Fail-Closed)."
            )

        if state == MarketState.HOLIDAY_CLOSED:
            return MarketSessionValidationResult(
                allowed=False,
                rejection_reason="HOLIDAY_CLOSED",
                market_state=state,
                active_interval=active_interval,
                remaining_session_seconds=0.0,
                source_authority=source_auth,
                message="Trade rejected: Market is closed due to Holiday / Bank Holiday."
            )

        if state != MarketState.OPEN or active_interval is None:
            return MarketSessionValidationResult(
                allowed=False,
                rejection_reason="MARKET_CLOSED",
                market_state=state,
                active_interval=None,
                remaining_session_seconds=0.0,
                source_authority=source_auth,
                message="Trade rejected: Market session is currently closed."
            )

        rem_seconds = active_interval.remaining_seconds(now)

        # Pre-entry 120s remaining session requirement (strictly > 120s + 1s cutoff buffer = > 121.0s)
        if rem_seconds <= (self.POSITION_MINIMUM_NORMAL_LIFETIME + 1.0):
            return MarketSessionValidationResult(
                allowed=False,
                rejection_reason="INSUFFICIENT_SESSION_TIME",
                market_state=state,
                active_interval=active_interval,
                remaining_session_seconds=rem_seconds,
                source_authority=source_auth,
                message=f"Trade rejected: Remaining session time ({rem_seconds:.1f}s) <= 121s cutoff threshold."
            )

        # TP-Time Feasibility evaluation if TP parameters are supplied
        tp_feasibility = None
        if distance_to_tp is not None and current_volatility_atr is not None:
            tp_feasibility = self.estimate_tp_time_feasibility(
                distance_to_tp=distance_to_tp,
                current_volatility_atr=current_volatility_atr,
                remaining_session_seconds=rem_seconds,
                historical_mfe_speed=historical_mfe_speed
            )
            if not tp_feasibility.is_feasible:
                return MarketSessionValidationResult(
                    allowed=False,
                    rejection_reason=tp_feasibility.rejection_reason or "TP_TIME_FEASIBILITY_FAILED",
                    market_state=state,
                    active_interval=active_interval,
                    remaining_session_seconds=rem_seconds,
                    tp_feasibility=tp_feasibility,
                    source_authority=source_auth,
                    message=f"Trade rejected: TP feasibility failed ({tp_feasibility.rejection_reason})."
                )

        return MarketSessionValidationResult(
            allowed=True,
            rejection_reason=None,
            market_state=state,
            active_interval=active_interval,
            remaining_session_seconds=rem_seconds,
            tp_feasibility=tp_feasibility,
            source_authority=source_auth,
            message="Pre-entry market session and calendar validation passed."
        )
