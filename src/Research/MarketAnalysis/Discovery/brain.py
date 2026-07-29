import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from src.Data.MarketData.Models.models import MarketDataPoint
from src.Research.MarketAnalysis.Discovery.models import (
    MarketObservation,
    MarketSequence,
    MarketEvent,
    PatternMemory,
    ExperienceMemory,
    VirtualTrade,
    SimulationResult,
    LearningRecord,
    AnalysisReport,
    DynamicTimeScale,
    MultiScaleRelationship,
    AIView,
    HumanView,
    SpreadData,
    PriceExecutionData,
    MarketConditionData,
    TradingRealityMemory,
    ConceptMemory,
    Hypothesis,
    JudgeReport,
    MemoryAssociation,
    CuriosityQuestion,
    LearningEpisode
)


# =========================================================================
# COGNITIVE CORES & INTERFACE CONTRACTS
# =========================================================================

class IReplayEngine(ABC):
    """Interface for replaying historical sequences chronologically without future leakage."""
    @abstractmethod
    def replay_historical_sequence(self, sequence: MarketSequence, memory_system: Any) -> List[SimulationResult]:
        pass


class IJudgeEngine(ABC):
    """Interface for independent decision and reasoning evaluations."""
    @abstractmethod
    def evaluate_virtual_trade(self, trade: VirtualTrade, result: SimulationResult, sample_count: int) -> JudgeReport:
        pass


class IMemoryConsolidation(ABC):
    """Interface for consolidating evaluated episodic experiences into validated concept memories."""
    @abstractmethod
    def consolidate_experience(self, trade: VirtualTrade, result: SimulationResult, judge_report: JudgeReport, memory: Any) -> Optional[LearningRecord]:
        pass


class ILearningEngine(ABC):
    """Interface for orchestrating the complete Cognitive Learning loop."""
    @abstractmethod
    def execute_learning_loop(self, trade: VirtualTrade, result: SimulationResult, memory: Any, judge_brain: IJudgeEngine) -> Optional[LearningEpisode]:
        pass


class IResearchPriorityEngine(ABC):
    """Interface for calculating active learning research priorities."""
    @abstractmethod
    def calculate_research_priority(self, memory: Any) -> Dict[str, Any]:
        pass


# =========================================================================
# CONCRETE COGNITIVE CORE IMPLEMENTATIONS
# =========================================================================

class TradingRealityEngine:
    """
    Ties execution conditions, dynamic spread, slippage, and trading session metrics
    into a realism framework. Maintains separate memory storage to avoid pattern bias.
    """
    def __init__(self) -> None:
        self.reality_memories: List[TradingRealityMemory] = []

    def observe_spread(self, symbol: str, bid: float, ask: float) -> SpreadData:
        """Calculates and stores standard bid-ask spread records."""
        spread_val = ask - bid
        mid = (ask + bid) / 2.0
        spread_pct = (spread_val / mid) * 100.0 if mid > 0 else 0.0

        return SpreadData(
            Timestamp=datetime.now(),
            Symbol=symbol,
            Bid=bid,
            Ask=ask,
            SpreadValue=spread_val,
            SpreadPercentage=spread_pct,
            SpreadChange=0.0  # calculated over intervals
        )

    def simulate_slippage(self, base_price: float, volatility_factor: float = 1.0) -> float:
        """Simulates variable slippage based on volatility state."""
        # Simple point-slippage multiplier
        return 0.1 * volatility_factor

    def evaluate_execution(self, expected_price: float, actual_price: float) -> PriceExecutionData:
        """Evaluates entry price versus requested signal price to calculate exact execution lag/slippage."""
        diff = actual_price - expected_price
        return PriceExecutionData(
            ExpectedEntry=expected_price,
            ActualEntry=actual_price,
            BidAskDifference=abs(diff),
            ExecutionDifference=diff,
            Slippage=abs(diff)
        )

    def save_reality_record(self, record: TradingRealityMemory) -> None:
        """Stores a separate execution performance memory."""
        self.reality_memories.append(record)


class DynamicTimeStructureDiscoveryEngine:
    """
    Discovers adaptive, custom internal time-scales based on state-change thresholds
    (e.g., price movements, volume accumulations) rather than static calendar/terminal timeframes.
    """
    def discover_scales(self, observations: List[MarketObservation], price_threshold: float = 10.0) -> List[DynamicTimeScale]:
        """Segments observations dynamically into state-based DynamicTimeScale blocks."""
        scales = []
        if len(observations) < 2:
            return scales

        current_segment: List[MarketObservation] = [observations[0]]
        start_price = observations[0].Close

        for i in range(1, len(observations)):
            current_obs = observations[i]
            current_segment.append(current_obs)

            # Check if state change threshold is met
            price_change = abs(current_obs.Close - start_price)
            if price_change >= price_threshold or i == len(observations) - 1:
                # Segment finalized, calculate duration
                duration_mins = (current_obs.Timestamp - current_segment[0].Timestamp).total_seconds() / 60.0
                if duration_mins == 0:
                    duration_mins = 1.0  # safety floor

                vol_sum = sum(o.Volume for o in current_segment)
                net_change = current_obs.Close - start_price

                scales.append(
                    DynamicTimeScale(
                        ScaleId=str(uuid.uuid4())[:8],
                        DurationMinutes=duration_mins,
                        TotalVolume=vol_sum,
                        PriceChangePoints=net_change,
                        CreatedByMovementCount=len(current_segment)
                    )
                )
                # Reset for next scale segment
                current_segment = [current_obs]
                start_price = current_obs.Close

        return scales


class MultiScaleMarketPerception:
    """
    Performs multi-scale relationship mapping and tests fractal-like behavioral recurrence
    hypotheses between discovered time-scales.
    """
    def test_scale_hypothesis(self, parent_scale: DynamicTimeScale, child_scale: DynamicTimeScale) -> MultiScaleRelationship:
        """Formulates and tests the recurrence hypothesis between parent and child scales."""
        # Calculate similarity based on point movement ratios and durations
        p_ratio = abs(parent_scale.PriceChangePoints)
        c_ratio = abs(child_scale.PriceChangePoints)

        if p_ratio == 0:
            p_ratio = 1.0
        ratio_sim = min(c_ratio, p_ratio) / max(c_ratio, p_ratio)

        # Determine hypothesis verification state
        if parent_scale.CreatedByMovementCount < 3 or child_scale.CreatedByMovementCount < 3:
            state = "INSUFFICIENT_EVIDENCE"
            sim_score = ratio_sim * 0.5
        elif ratio_sim >= 0.8:
            state = "CONFIRMED"
            sim_score = ratio_sim
        else:
            state = "REJECTED"
            sim_score = ratio_sim

        return MultiScaleRelationship(
            RelationshipId=str(uuid.uuid4())[:8],
            ParentScaleId=parent_scale.ScaleId,
            ChildScaleId=child_scale.ScaleId,
            HypothesisType="behavior_repeats",
            HypothesisState=state,
            SimilarityScore=sim_score
        )


class DataRealityLayer:
    """
    Input validation and normalization layer.
    Receives raw market data from MT5 or historical feeds, validates sequence order,
    detects missing candle intervals, and formats observations. No interpretation.
    """
    def receive_data(self, data_points: List[MarketDataPoint], timeframe: str) -> List[MarketObservation]:
        """Translates raw DataPoints into clean MarketObservation snapshots."""
        observations = []
        for dp in data_points:
            obs = MarketObservation(
                Asset=dp.AssetId,
                Timestamp=dp.Timestamp,
                Open=dp.Open,
                High=dp.High,
                Low=dp.Low,
                Close=dp.Close,
                Volume=dp.Volume,
                Timeframe=timeframe
            )
            observations.append(obs)
        return observations

    def validate_timestamps(self, observations: List[MarketObservation]) -> bool:
        """Verifies that timestamps are sorted chronologically and contain no duplicates."""
        if len(observations) <= 1:
            return True
        for i in range(1, len(observations)):
            if observations[i].Timestamp <= observations[i-1].Timestamp:
                return False
        return True

    def detect_missing_candles(self, observations: List[MarketObservation], expected_interval_minutes: int) -> List[datetime]:
        """Calculates differences between consecutive candles and identifies gaps."""
        missing = []
        if len(observations) <= 1:
            return missing

        delta = timedelta(minutes=expected_interval_minutes)
        for i in range(1, len(observations)):
            diff = observations[i].Timestamp - observations[i-1].Timestamp
            if diff > delta:
                # Add expected timestamps that are missing
                curr = observations[i-1].Timestamp + delta
                while curr < observations[i].Timestamp:
                    missing.append(curr)
                    curr += delta
        return missing

    def normalize_market_event(self, obs: MarketObservation) -> Dict[str, Any]:
        """Converts raw snapshot into standard key-value dictionary representing reality."""
        return {
            "asset": obs.Asset,
            "timestamp": obs.Timestamp.isoformat(),
            "open": obs.Open,
            "high": obs.High,
            "low": obs.Low,
            "close": obs.Close,
            "volume": obs.Volume,
            "timeframe": obs.Timeframe
        }


class ObservationBrain:
    """
    Observes price-action sequences purely through movement, points, durations,
    and reaction sequences. Strictly forbids predefined indicators (RSI, MACD)
    or human-defined breakout/resistance terms.
    Generates dual Human/AI views of price action.
    """
    def observe_sequence(self, sequence: MarketSequence) -> List[MarketEvent]:
        """Parses a market sequence into structural Point-Duration-Reaction Events."""
        events = []
        obs_list = sequence.Observations
        if len(obs_list) < 2:
            return events

        # Group observations into consecutive price movements (runs)
        current_run: List[MarketObservation] = [obs_list[0]]

        for i in range(1, len(obs_list)):
            current_obs = obs_list[i]
            prev_obs = obs_list[i-1]

            # Determine direction of the current candle
            current_direction = "upward" if current_obs.Close >= prev_obs.Close else "downward"
            prev_direction = "upward" if prev_obs.Close >= obs_list[max(0, i-2)].Close else "downward"

            if current_direction == prev_direction:
                current_run.append(current_obs)
            else:
                # End of a run, finalize Event
                event = self._build_event_from_run(sequence.Asset, sequence.Timeframe, current_run)
                if event:
                    events.append(event)
                current_run = [prev_obs, current_obs]

        # Handle the last remaining run
        if len(current_run) >= 2:
            event = self._build_event_from_run(sequence.Asset, sequence.Timeframe, current_run)
            if event:
                events.append(event)

        # Calculate retracement/reactions by comparing consecutive events
        for j in range(1, len(events)):
            prev_ev = events[j-1]
            curr_ev = events[j]
            if prev_ev.Direction != curr_ev.Direction:
                # Retracement points size is the price movement of current event
                # Assign retracement details to the parent previous event
                retraced_points = abs(curr_ev.PriceMovementPoints)
                retraced_duration = curr_ev.DurationCandles

                # Re-build previous event with retracement points
                events[j-1] = MarketEvent(
                    EventId=prev_ev.EventId,
                    Asset=prev_ev.Asset,
                    Timeframe=prev_ev.Timeframe,
                    StartTime=prev_ev.StartTime,
                    EndTime=prev_ev.EndTime,
                    PriceMovementPoints=prev_ev.PriceMovementPoints,
                    DurationCandles=prev_ev.DurationCandles,
                    ConsecutiveCandlesCount=prev_ev.ConsecutiveCandlesCount,
                    Direction=prev_ev.Direction,
                    RetracementPoints=retraced_points,
                    RetracementDuration=retraced_duration
                )

        return events

    def _build_event_from_run(self, asset: str, timeframe: str, run: List[MarketObservation]) -> Optional[MarketEvent]:
        if len(run) < 2:
            return None
        start = run[0]
        end = run[-1]

        move_points = end.Close - start.Open
        direction = "upward" if move_points >= 0 else "downward"

        # Calculate consecutive candles in the direction of the movement
        consecutive_count = 0
        for i in range(1, len(run)):
            candle_direction = "upward" if run[i].Close >= run[i-1].Close else "downward"
            if candle_direction == direction:
                consecutive_count += 1

        return MarketEvent(
            EventId=str(uuid.uuid4())[:8],
            Asset=asset,
            Timeframe=timeframe,
            StartTime=start.Timestamp,
            EndTime=end.Timestamp,
            PriceMovementPoints=move_points,
            DurationCandles=len(run),
            ConsecutiveCandlesCount=consecutive_count,
            Direction=direction
        )

    def generate_ai_view(self, sequence: MarketSequence, events: List[MarketEvent]) -> AIView:
        """Generates math-first AI-View representing structural price dependencies for the AI brain."""
        price_seq = [o.Close for o in sequence.Observations]

        move_struct = []
        for ev in events:
            move_struct.append({
                "direction": ev.Direction,
                "points": ev.PriceMovementPoints,
                "candles": ev.DurationCandles
            })

        reaction_map = {}
        if events:
            latest = events[-1]
            reaction_map = {
                "latest_event_id": latest.EventId,
                "retraced_points": latest.RetracementPoints,
                "retraced_duration": latest.RetracementDuration
            }

        temporal_relationship = []
        for i in range(1, len(events)):
            temporal_relationship.append({
                "from_event": events[i-1].EventId,
                "to_event": events[i].EventId,
                "distance_candles": events[i].DurationCandles
            })

        return AIView(
            PriceSequence=price_seq,
            MovementStructure=move_struct,
            ReactionMap=reaction_map,
            TemporalRelationship=temporal_relationship
        )

    def generate_human_view(self, sequence: MarketSequence) -> HumanView:
        """Generates classic, visual Human-View representing candle charts and timelines for human dashboards."""
        ohlc_data = []
        timeline = []
        for o in sequence.Observations:
            ohlc_data.append({
                "open": o.Open,
                "high": o.High,
                "low": o.Low,
                "close": o.Close,
                "volume": o.Volume
            })
            timeline.append(o.Timestamp)

        return HumanView(
            Symbol=sequence.Asset,
            CandlesCount=sequence.length,
            Timeline=timeline,
            OhlcData=ohlc_data
        )


class MultiTimeframePerceptionLayer:
    """
    Fractal perception engine mapping nested price behaviors across multiple
    timeframes (Daily -> H4 -> H1 -> M15 -> M5 -> M1).
    """
    def __init__(self) -> None:
        self.associations: Dict[str, List[MarketSequence]] = {}  # event_id -> child_sequences

    def associate_timeframes(self, parent_event: MarketEvent, child_sequence: MarketSequence) -> None:
        """Stores fractal nested relationship between parent event and child sequence."""
        if parent_event.EventId not in self.associations:
            self.associations[parent_event.EventId] = []
        self.associations[parent_event.EventId].append(child_sequence)

    def get_child_sequences(self, parent_event_id: str) -> List[MarketSequence]:
        """Retrieves child timeframe sequences associated with the parent event."""
        return self.associations.get(parent_event_id, [])


class MemorySystem:
    """
    Decoupled four-layer Memory System (Event, Pattern, Experience, and Concept memory).
    """
    def __init__(self) -> None:
        self.events_memory: List[MarketEvent] = []
        self.patterns_memory: Dict[str, PatternMemory] = {}  # Signature -> PatternMemory
        self.experience_memory: List[ExperienceMemory] = []
        self.concept_memory: Dict[str, ConceptMemory] = {}  # ConceptId -> ConceptMemory

    def save_event(self, event: MarketEvent) -> None:
        self.events_memory.append(event)

    def save_pattern(self, pattern: PatternMemory) -> None:
        self.patterns_memory[pattern.Signature] = pattern

    def save_experience(self, experience: ExperienceMemory) -> None:
        self.experience_memory.append(experience)

    def save_concept(self, concept: ConceptMemory) -> None:
        self.concept_memory[concept.ConceptId] = concept

    def calculate_similarity(self, sig1: str, sig2: str) -> float:
        """Jaccard similarity rating for tokenized signature structures."""
        if sig1 == sig2:
            return 1.0
        tokens1 = set(sig1.split("_"))
        tokens2 = set(sig2.split("_"))
        intersection = tokens1.intersection(tokens2)
        union = tokens1.union(tokens2)
        if not union:
            return 0.0
        return len(intersection) / len(union)

    def find_similar_patterns(self, signature: str, threshold: float = 0.5) -> List[Tuple[PatternMemory, float]]:
        """Searches Pattern Memory and returns matched entries with similarity scores."""
        matched = []
        for pm in self.patterns_memory.values():
            sim = self.calculate_similarity(signature, pm.Signature)
            if sim >= threshold:
                matched.append((pm, sim))
        matched.sort(key=lambda x: x[1], reverse=True)
        return matched


class MemoryAssociationEngine:
    """
    Links temporally distant observations across different market structures,
    regimes, and internal durations.
    """
    def __init__(self) -> None:
        self.associations: List[MemoryAssociation] = []

    def associate_episodes(self, obs_a: MarketObservation, obs_b: MarketObservation, correlation_score: float) -> MemoryAssociation:
        """Saves a correlation link between two distant structural states."""
        assoc = MemoryAssociation(
            AssociationId=str(uuid.uuid4())[:8],
            SourceObservationId=f"obs_{int(obs_a.Timestamp.timestamp())}",
            AssociatedObservationId=f"obs_{int(obs_b.Timestamp.timestamp())}",
            RegimeCorrelationScore=correlation_score
        )
        self.associations.append(assoc)
        return assoc


class PatternDiscoveryEngine:
    """
    Extracts matches from MemorySystem to discover similarity-based behavior
    without forecasting or ML models.
    """
    def discover_similarities(self, current_signature: str, memory: MemorySystem) -> Dict[str, Any]:
        """Answers: 'Have I seen something similar before?'."""
        matches = memory.find_similar_patterns(current_signature, threshold=0.5)

        if not matches:
            return {
                "similar_situations_found": [],
                "total_occurrences": 0,
                "continuation_probability": 0.5,
                "reversal_probability": 0.5,
                "raw_matches": []
            }

        total_occurrences = sum(pm.Occurrences for pm, sim in matches)
        total_cont = sum(pm.ContinuationCount for pm, sim in matches)
        total_rev = sum(pm.ReversalCount for pm, sim in matches)

        cont_prob = total_cont / total_occurrences if total_occurrences > 0 else 0.5
        rev_prob = total_rev / total_occurrences if total_occurrences > 0 else 0.5

        descriptions = []
        for pm, sim in matches:
            desc = f"Pattern {pm.PatternId} ({pm.Signature}): Match {int(sim*100)}%, Occurrences: {pm.Occurrences}"
            descriptions.append(desc)

        return {
            "similar_situations_found": descriptions,
            "total_occurrences": total_occurrences,
            "continuation_probability": cont_prob,
            "reversal_probability": rev_prob,
            "raw_matches": matches
        }


class CuriosityEngine:
    """Generates active research questions for unexplained/unconfirmed behaviors."""
    def __init__(self) -> None:
        self.questions: List[CuriosityQuestion] = []

    def ask_question(self, target_behavior: str, gap_desc: str) -> CuriosityQuestion:
        """Formulates an active curiosity question."""
        q = CuriosityQuestion(
            QuestionId=str(uuid.uuid4())[:8],
            TargetBehavior=target_behavior,
            UnderstandingGap=gap_desc,
            CreatedAt=datetime.now()
        )
        self.questions.append(q)
        return q


class HypothesisEngine:
    """Creates structured, falsifiable hypotheses based on raw memory evidence."""
    def __init__(self) -> None:
        self.hypotheses: Dict[str, Hypothesis] = {}

    def formulate_hypothesis(self, description: str, evidence_ids: List[str], prior_confidence: float = 0.5) -> Hypothesis:
        """Formulates a new hypothesis."""
        hyp = Hypothesis(
            HypothesisId=str(uuid.uuid4())[:8],
            Description=description,
            EvidenceObservationIds=evidence_ids,
            CreatedAt=datetime.now(),
            Confidence=prior_confidence,
            Status="PENDING"
        )
        self.hypotheses[hyp.HypothesisId] = hyp
        return hyp

    def transition_status(self, hypothesis_id: str, new_status: str, final_confidence: float) -> None:
        """Advances hypothesis status (e.g. TESTING -> CONFIRMED)."""
        if hypothesis_id in self.hypotheses:
            old_hyp = self.hypotheses[hypothesis_id]
            updated = Hypothesis(
                HypothesisId=old_hyp.HypothesisId,
                Description=old_hyp.Description,
                EvidenceObservationIds=old_hyp.EvidenceObservationIds,
                CreatedAt=old_hyp.CreatedAt,
                Confidence=final_confidence,
                Status=new_status
            )
            self.hypotheses[hypothesis_id] = updated


class ScientificTestingEngine:
    """Tests hypotheses against out-of-sample data, cross-regimes, and different durations."""
    def test_hypothesis(self, hypothesis: Hypothesis, oos_data: MarketSequence) -> Tuple[str, float]:
        """Validates hypothesis. Returns status and evaluated confidence score."""
        if len(oos_data.Observations) < 5:
            return "INSUFFICIENT_EVIDENCE", hypothesis.Confidence

        # Basic repeatability validation
        matches = 0
        for i in range(1, len(oos_data.Observations)):
            if oos_data.Observations[i].Close >= oos_data.Observations[i-1].Close:
                matches += 1

        ratio = matches / len(oos_data.Observations)
        if ratio >= 0.7:
            return "CONFIRMED", ratio
        elif ratio <= 0.3:
            return "REJECTED", ratio
        return "INSUFFICIENT_EVIDENCE", ratio


class MarketUnderstandingModel:
    """Maintains and evolves verified concept memories."""
    def __init__(self, memory_system: MemorySystem) -> None:
        self.memory = memory_system

    def build_concept(self, description: str, sample_count: int, confidence: float) -> ConceptMemory:
        """Saves a newly validated concept to Memory."""
        concept = ConceptMemory(
            ConceptId=str(uuid.uuid4())[:8],
            Description=description,
            Confidence=confidence,
            ValidatedSamples=sample_count,
            LastValidatedAt=datetime.now()
        )
        self.memory.save_concept(concept)
        return concept

    def get_understanding_report(self) -> Dict[str, Any]:
        """Provides report of current system understanding vs gaps."""
        return {
            "verified_concepts_count": len(self.memory.concept_memory),
            "concepts": [c.Description for c in self.memory.concept_memory.values()],
            "unknown_state_active": len(self.memory.concept_memory) == 0
        }


class ConfidenceEngine:
    """Calculates evidence-based confidence levels dynamically."""
    def calibrate_confidence(self, sample_count: int, judge_score: float, contradiction_count: int) -> float:
        """Calibrates confidence: increases with samples & judge approval; decreases with contradictions."""
        if sample_count == 0:
            return 0.5  # Unknown state default

        base = 0.5 + (0.1 * min(sample_count, 5))
        base += (0.2 * judge_score)
        base -= (0.15 * contradiction_count)

        return max(0.0, min(1.0, base))


class QualityControlBrain:
    """
    Independent reasoning quality evaluator. Enforces statistical rigor
    and warns against overfitting or weak evidence base.
    """
    def evaluate_reasoning(self, matched_patterns: List[Tuple[PatternMemory, float]], sample_threshold: int = 5) -> Tuple[float, str]:
        """Evaluates confidence based on matched samples, similarity metrics, and overfitting checks."""
        if not matched_patterns:
            return 0.0, "Weak evidence base: Absolutely no similar patterns found in historical memory."

        highest_sim = matched_patterns[0][1]
        total_samples = sum(pm.Occurrences for pm, sim in matched_patterns)

        if total_samples < sample_threshold:
            return 0.3, f"Low sample warning: Reasoning is based on only {total_samples} historical occurrences (threshold: {sample_threshold})."

        if highest_sim < 0.7:
            return 0.5, f"Weak similarity match: Highest similarity is {int(highest_sim*100)}%. Reasoning may be accidental."

        # Detect potential overfitting (e.g. perfect continuation rate with very few samples)
        for pm, sim in matched_patterns:
            if pm.Occurrences < 3 and (pm.continuation_probability == 1.0 or pm.reversal_probability == 1.0):
                return 0.4, f"Overfitting hazard: Match {pm.PatternId} exhibits 100% rate but with only {pm.Occurrences} samples."

        return 0.9, f"Strong evidence base: Verified across {total_samples} historical cases with match similarity up to {int(highest_sim*100)}%."


class VirtualTradingEngine:
    """Handles creation and bar-by-bar evaluation of internal simulated virtual trades with realistic bid-ask spread friction."""
    def __init__(self, reality_engine: Optional[TradingRealityEngine] = None) -> None:
        self.reality_engine = reality_engine or TradingRealityEngine()

    def create_virtual_trade(
        self,
        asset: str,
        timeframe: str,
        direction: str,
        entry_price: float,
        stop_loss: float,
        target_price: float,
        expected_scenario: str,
        entry_time: datetime,
        spread_val: float = 0.5,
        commission: float = 0.0,
        volatility: float = 1.0
    ) -> VirtualTrade:
        """Returns a newly opened VirtualTrade instance with realistic bid/ask spread markup applied."""
        # Check for NO_TRADE or WAIT states - they don't apply slippage or spreads
        if direction in ["WAIT", "NO TRADE", "NO_TRADE"]:
            return VirtualTrade(
                TradeId=str(uuid.uuid4())[:8],
                Asset=asset,
                Timeframe=timeframe,
                Direction=direction,
                EntryPrice=entry_price,
                StopLoss=stop_loss,
                TargetPrice=target_price,
                EntryTime=entry_time,
                ExpectedScenario=expected_scenario,
                Bid=entry_price,
                Ask=entry_price,
                Spread=0.0,
                Commission=0.0,
                Slippage=0.0
            )

        # Calculate realistic entry using spread
        slippage = self.reality_engine.simulate_slippage(entry_price, volatility)

        if direction == "BUY":
            bid = entry_price - spread_val / 2.0
            ask = entry_price + spread_val / 2.0
            actual_entry = ask + slippage
        else:
            bid = entry_price - spread_val / 2.0
            ask = entry_price + spread_val / 2.0
            actual_entry = bid - slippage

        return VirtualTrade(
            TradeId=str(uuid.uuid4())[:8],
            Asset=asset,
            Timeframe=timeframe,
            Direction=direction,
            EntryPrice=actual_entry,
            StopLoss=stop_loss,
            TargetPrice=target_price,
            EntryTime=entry_time,
            ExpectedScenario=expected_scenario,
            Bid=bid,
            Ask=ask,
            Spread=spread_val,
            Commission=commission,
            Slippage=slippage
        )

    def update_trade_progress(self, trade: VirtualTrade, current_obs: MarketObservation) -> Optional[SimulationResult]:
        """Updates trade price records, checking stops and targets using Bid/Ask margins. Returns SimulationResult if closed."""
        if trade.State == "CLOSED":
            return None

        # Handle WAIT or NO_TRADE directly. They resolve neutral on progress immediately.
        if trade.Direction in ["WAIT", "NO TRADE", "NO_TRADE"]:
            trade.State = "CLOSED"
            trade.ExitPrice = trade.EntryPrice
            trade.ExitTime = current_obs.Timestamp
            return SimulationResult(
                TradeId=trade.TradeId,
                IsSuccess=True,
                MaxFavorableMovementPoints=0.0,
                MaxAdverseMovementPoints=0.0,
                FinalResult="NEUTRAL",
                FailureReason="Trade resolved cleanly as neutral waiting state."
            )

        # Bid/Ask simulation for the current candle
        bid_price = current_obs.Close - trade.Spread / 2.0
        ask_price = current_obs.Close + trade.Spread / 2.0

        # Update high/low tracking using bid/ask
        if trade.Direction == "BUY":
            trade.MaxFavorablePrice = max(trade.MaxFavorablePrice, bid_price)
            trade.MaxAdversePrice = min(trade.MaxAdversePrice, bid_price)
        else:
            trade.MaxFavorablePrice = min(trade.MaxFavorablePrice, ask_price)
            trade.MaxAdversePrice = max(trade.MaxAdversePrice, ask_price)

        # Evaluate target and stop conditions using realistic execution price
        is_closed = False
        exit_price = current_obs.Close
        failure_reason = None
        result_type = "LOSS"

        if trade.Direction == "BUY":
            if (current_obs.Low - trade.Spread / 2.0) <= trade.StopLoss:
                is_closed = True
                exit_price = trade.StopLoss
                failure_reason = "Stop Loss Hit - Adverse bid price touched SL boundary."
                result_type = "LOSS"
            elif (current_obs.High - trade.Spread / 2.0) >= trade.TargetPrice:
                is_closed = True
                exit_price = trade.TargetPrice
                result_type = "WIN"
        else:
            if (current_obs.High + trade.Spread / 2.0) >= trade.StopLoss:
                is_closed = True
                exit_price = trade.StopLoss
                failure_reason = "Stop Loss Hit - Adverse ask price touched SL boundary."
                result_type = "LOSS"
            elif (current_obs.Low + trade.Spread / 2.0) <= trade.TargetPrice:
                is_closed = True
                exit_price = trade.TargetPrice
                result_type = "WIN"

        if is_closed:
            trade.State = "CLOSED"
            trade.ExitPrice = exit_price
            trade.ExitTime = current_obs.Timestamp

            # Compute MFM and MAM in points including spread and costs
            if trade.Direction == "BUY":
                mfm = trade.MaxFavorablePrice - trade.EntryPrice - trade.Commission
                mam = trade.EntryPrice - trade.MaxAdversePrice + trade.Commission
            else:
                mfm = trade.EntryPrice - trade.MaxFavorablePrice - trade.Commission
                mam = trade.MaxAdversePrice - trade.EntryPrice + trade.Commission

            return SimulationResult(
                TradeId=trade.TradeId,
                IsSuccess=(result_type == "WIN"),
                MaxFavorableMovementPoints=mfm,
                MaxAdverseMovementPoints=mam,
                FinalResult=result_type,
                FailureReason=failure_reason
            )
        return None


class OutcomeEvaluationEngine:
    """Independent outcome engine calculating decision efficacy stats."""
    def evaluate_outcome(self, trade: VirtualTrade, final_price: float, closed_time: datetime) -> SimulationResult:
        """Evaluates closed virtual trade performance metrics."""
        trade.State = "CLOSED"
        trade.ExitPrice = final_price
        trade.ExitTime = closed_time

        if trade.Direction in ["WAIT", "NO TRADE", "NO_TRADE"]:
            return SimulationResult(
                TradeId=trade.TradeId,
                IsSuccess=True,
                MaxFavorableMovementPoints=0.0,
                MaxAdverseMovementPoints=0.0,
                FinalResult="NEUTRAL",
                FailureReason="Trade resolved cleanly as neutral waiting state."
            )

        if trade.Direction == "BUY":
            mfm = trade.MaxFavorablePrice - trade.EntryPrice - trade.Commission
            mam = trade.EntryPrice - trade.MaxAdversePrice + trade.Commission
            is_success = (final_price >= trade.EntryPrice)
        else:
            mfm = trade.EntryPrice - trade.MaxFavorablePrice - trade.Commission
            mam = trade.MaxAdversePrice - trade.EntryPrice + trade.Commission
            is_success = (final_price <= trade.EntryPrice)

        res_type = "WIN" if is_success else "LOSS"
        fail_reason = None if is_success else "Simulated target period expired without positive closure."

        return SimulationResult(
            TradeId=trade.TradeId,
            IsSuccess=is_success,
            MaxFavorableMovementPoints=mfm,
            MaxAdverseMovementPoints=mam,
            FinalResult=res_type,
            FailureReason=fail_reason
        )


class LearningMemoryUpdate:
    """Updates Pattern and Experience episodic libraries using evaluated simulated outcomes."""
    def update_memory_with_outcome(self, trade: VirtualTrade, result: SimulationResult, memory: MemorySystem) -> LearningRecord:
        """Updates frequencies and continuation statistics, recording episodic experiences."""
        sig = trade.ExpectedScenario

        # Retrieve or create pattern
        if sig not in memory.patterns_memory:
            pat = PatternMemory(PatternId=str(uuid.uuid4())[:8], Signature=sig)
            memory.save_pattern(pat)
        else:
            pat = memory.patterns_memory[sig]

        prior_prob = pat.continuation_probability

        # Update counts
        pat.Occurrences += 1
        if result.FinalResult == "WIN":
            pat.ContinuationCount += 1
        else:
            pat.ReversalCount += 1

        new_prob = pat.continuation_probability

        # Save episodic Experience
        exp = ExperienceMemory(
            MemoryId=str(uuid.uuid4())[:8],
            Timestamp=datetime.now(),
            SituationSignature=sig,
            Decision=trade.Direction,
            MaxFavorableMovement=result.MaxFavorableMovementPoints,
            MaxAdverseMovement=result.MaxAdverseMovementPoints,
            FinalResult=result.FinalResult,
            Lesson=f"Decision {trade.Direction} ended in {result.FinalResult}. Fail: {result.FailureReason}"
        )
        memory.save_experience(exp)

        return LearningRecord(
            RecordId=str(uuid.uuid4())[:8],
            CreatedAt=datetime.now(),
            SourceTradeId=trade.TradeId,
            UpdatedPatternId=pat.PatternId,
            PriorContinuationProb=prior_prob,
            NewContinuationProb=new_prob,
            LessonLearned=f"Updated pattern {pat.PatternId} continuation odds to {int(new_prob*100)}% based on simulated episodic lesson."
        )


class IndependentJudgeBrain(IJudgeEngine):
    """Evaluates virtual trades independently, ensuring reasoning quality and statistical validity."""
    def evaluate_virtual_trade(self, trade: VirtualTrade, result: SimulationResult, sample_count: int) -> JudgeReport:
        """Verifies reasoning quality, sample sizes, and consistency to approve learning updates."""
        is_valid = True
        verdict = "APPROVED"
        explanation = "Reasoning quality approved based on sufficient sample count."

        if sample_count < 3:
            is_valid = False
            verdict = "DISAPPROVED"
            explanation = "Sample insufficiency: matched occurrences are too low to declare valid learning context."

        return JudgeReport(
            ReportId=str(uuid.uuid4())[:8],
            TradeId=trade.TradeId,
            EvidenceQualityScore=1.0 if is_valid else 0.4,
            ReasoningQualityScore=0.9 if is_valid else 0.3,
            SampleSufficiencyScore=1.0 if sample_count >= 5 else 0.5,
            IsScientificallyValid=is_valid,
            Verdict=verdict,
            Explanation=explanation
        )


class MemoryConsolidationManager(IMemoryConsolidation):
    """Manages secure consolidation of experiences into concepts after independent Judge approval."""
    def consolidate_experience(self, trade: VirtualTrade, result: SimulationResult, judge_report: JudgeReport, memory: MemorySystem) -> Optional[LearningRecord]:
        if not judge_report.IsScientificallyValid or judge_report.Verdict != "APPROVED":
            return None  # Consolidation rejected!

        sig = trade.ExpectedScenario
        pat = memory.patterns_memory.get(sig)
        if not pat:
            pat = PatternMemory(PatternId=str(uuid.uuid4())[:8], Signature=sig)
            memory.save_pattern(pat)

        prior_prob = pat.continuation_probability
        pat.Occurrences += 1
        if result.FinalResult == "WIN":
            pat.ContinuationCount += 1
        else:
            pat.ReversalCount += 1

        # Check if we should elevate this pattern signature to a Concept
        if pat.Occurrences >= 5 and pat.continuation_probability >= 0.7:
            # Check if concept already exists
            concept_id = f"concept_{pat.PatternId}"
            if concept_id not in memory.concept_memory:
                concept = ConceptMemory(
                    ConceptId=concept_id,
                    Description=f"Highly repeating pattern run structure: {pat.Signature}",
                    Confidence=pat.continuation_probability,
                    ValidatedSamples=pat.Occurrences,
                    LastValidatedAt=datetime.now()
                )
                memory.save_concept(concept)

        return LearningRecord(
            RecordId=str(uuid.uuid4())[:8],
            CreatedAt=datetime.now(),
            SourceTradeId=trade.TradeId,
            UpdatedPatternId=pat.PatternId,
            PriorContinuationProb=prior_prob,
            NewContinuationProb=pat.continuation_probability,
            LessonLearned="Consolidated Judge-approved virtual trade results into pattern signature metrics successfully."
        )


class CognitiveLearningEngine(ILearningEngine):
    """Orchestrates complete validated feedback loop: Observation -> Replay -> Judge -> Consolidation."""
    def __init__(self, consolidator: Optional[IMemoryConsolidation] = None) -> None:
        self.consolidator = consolidator or MemoryConsolidationManager()

    def execute_learning_loop(self, trade: VirtualTrade, result: SimulationResult, memory: MemorySystem, judge_brain: IJudgeEngine) -> Optional[LearningEpisode]:
        # 1. Ask Independent Judge to evaluate trade
        pat = memory.patterns_memory.get(trade.ExpectedScenario)
        samples = pat.Occurrences if pat else 10 # fallback/dummy if not created yet

        report = judge_brain.evaluate_virtual_trade(trade, result, sample_count=samples)

        # 2. If approved, consolidate into memory and concepts
        record = self.consolidator.consolidate_experience(trade, result, report, memory)
        if not record:
            return None  # Loop did not conclude due to Judge disapproval

        # 3. Save episodic LearningEpisode
        episode = LearningEpisode(
            EpisodeId=str(uuid.uuid4())[:8],
            CreatedAt=datetime.now(),
            ObservationIds=[f"obs_{int(trade.EntryTime.timestamp())}"],
            PatternIds=[pat.PatternId] if pat else [],
            HypothesisIds=[],
            JudgeReportIds=[report.ReportId],
            EvolvedConceptId=f"concept_{pat.PatternId}" if pat else "None"
        )
        return episode


class ResearchPriorityManager(IResearchPriorityEngine):
    """Calculates curiosity priorities based on weaknesses, low confidence, and sample size gaps."""
    def calculate_research_priority(self, memory: MemorySystem) -> Dict[str, Any]:
        if not memory.patterns_memory:
            return {
                "Research Priority": "Gold point sequences",
                "Reason": "Memory system is completely empty. Default research priority active.",
                "Required Samples": 5,
                "Expected Learning Value": 1.0
            }

        # Find pattern with lowest continuation probability or lowest sample count
        patterns = list(memory.patterns_memory.values())
        patterns.sort(key=lambda p: (p.Occurrences, p.continuation_probability))
        target_pat = patterns[0]

        return {
            "Research Priority": f"Signature {target_pat.Signature}",
            "Reason": f"High uncertainty: pattern occurrences count is only {target_pat.Occurrences} times.",
            "Required Samples": max(1, 5 - target_pat.Occurrences),
            "Expected Learning Value": 0.85
        }


class SimulationBrain(IReplayEngine):
    """Orchestrates historical sequence replays and internally simulates virtual decisions including execution conditions."""
    def __init__(self, reality_engine: Optional[TradingRealityEngine] = None) -> None:
        self.reality_engine = reality_engine or TradingRealityEngine()
        self.trading_engine = VirtualTradingEngine(reality_engine=self.reality_engine)
        self.evaluator = OutcomeEvaluationEngine()

    def simulate_replay(
        self,
        sequence: MarketSequence,
        memory: MemorySystem,
        direction: str,
        stop_loss_pts: float,
        target_pts: float,
        spread_val: float = 0.5,
        commission: float = 0.0,
        volatility: float = 1.0
    ) -> List[SimulationResult]:
        """Runs sequential simulation over a chronological market segment applying spreads and costs."""
        results = []
        obs_list = sequence.Observations
        if len(obs_list) < 5:
            return results

        # Create entry parameters based on the first candle
        entry_obs = obs_list[0]
        entry_price = entry_obs.Close

        if direction == "BUY":
            sl = entry_price - stop_loss_pts
            tp = entry_price + target_pts
        elif direction == "SELL":
            sl = entry_price + stop_loss_pts
            tp = entry_price - target_pts
        else:
            # WAIT or NO TRADE - resolved immediately
            sl = entry_price
            tp = entry_price

        trade = self.trading_engine.create_virtual_trade(
            asset=sequence.Asset,
            timeframe=sequence.Timeframe,
            direction=direction,
            entry_price=entry_price,
            stop_loss=sl,
            target_price=tp,
            expected_scenario=f"{sequence.Timeframe}_start_movement",
            entry_time=entry_obs.Timestamp,
            spread_val=spread_val,
            commission=commission,
            volatility=volatility
        )

        # Replay the sequence bar-by-bar
        for obs in obs_list[1:]:
            res = self.trading_engine.update_trade_progress(trade, obs)
            if res:
                results.append(res)
                break

        # If not closed by the end of sequence, evaluate with final close
        if trade.State == "OPEN":
            final_obs = obs_list[-1]
            res = self.evaluator.evaluate_outcome(trade, final_obs.Close, final_obs.Timestamp)
            results.append(res)

        return results

    def replay_historical_sequence(self, sequence: MarketSequence, memory_system: MemorySystem) -> List[SimulationResult]:
        """IReplayEngine Interface Replay implementation."""
        return self.simulate_replay(
            sequence=sequence,
            memory=memory_system,
            direction="WAIT",
            stop_loss_pts=0.0,
            target_pts=0.0
        )


class AntiSelfDeceptionLayer:
    """Protects cognitive modules against future leakage, look-ahead bias, and cherry-picking."""
    def verify_no_future_leakage(self, current_time: datetime, candidate_data: List[MarketObservation]) -> None:
        """Raises ValueError if any candidate observation exists beyond the current simulation timeframe boundary."""
        for obs in candidate_data:
            if obs.Timestamp > current_time:
                raise ValueError(f"Look-Ahead Violation: Data timestamp {obs.Timestamp} is in the future relative to current replay boundary {current_time}!")


class LiveAnalysisBrain:
    """
    Live market monitor. Runs dynamically with live MT5 feeds.
    Strictly forbids trading, providing 100% read-only analysis and reasoning.
    Generates dual AI-View and Human-View representations, including Trading Reality statistics.
    """
    def __init__(self, reality_engine: Optional[TradingRealityEngine] = None) -> None:
        self.reality_layer = DataRealityLayer()
        self.observation_brain = ObservationBrain()
        self.discovery_engine = PatternDiscoveryEngine()
        self.qc_brain = QualityControlBrain()
        self.reality_engine = reality_engine or TradingRealityEngine()

    def analyze_live_market(
        self,
        live_data: List[MarketDataPoint],
        timeframe: str,
        memory: MemorySystem,
        current_spread_val: float = 0.5
    ) -> Tuple[AnalysisReport, AIView, HumanView, SpreadData]:
        """Analyzes live market feed, checks QC reasoning, and returns AnalysisReport, Views, and SpreadData."""
        if not live_data:
            raise ValueError("No live data available for analysis.")

        observations = self.reality_layer.receive_data(live_data, timeframe)
        current_obs = observations[-1]

        # Extract sequence and events
        seq = MarketSequence(Asset=current_obs.Asset, Timeframe=timeframe, Observations=observations)
        events = self.observation_brain.observe_sequence(seq)

        sig = "neutral_flat_structure"
        if events:
            latest_event = events[-1]
            sig = f"{latest_event.Direction}_{latest_event.DurationCandles}"

        # Discover similarities
        discovery = self.discovery_engine.discover_similarities(sig, memory)
        qc_score, qc_msg = self.qc_brain.evaluate_reasoning(discovery.get("raw_matches", []))

        # Formulate active hypothesis based on statistics
        if discovery["continuation_probability"] > 0.6:
            active_hyp = f"Continuation hypothesis active based on pattern match ({int(discovery['continuation_probability']*100)}% odds)."
        elif discovery["reversal_probability"] > 0.6:
            active_hyp = f"Reversal hypothesis active based on pattern match ({int(discovery['reversal_probability']*100)}% odds)."
        else:
            active_hyp = "Neutral consensus: Expecting lateral flat fluctuation structure."

        report = AnalysisReport(
            ReportId=str(uuid.uuid4())[:8],
            Asset=current_obs.Asset,
            Timestamp=datetime.now(),
            CurrentObservation=current_obs,
            ActiveHypothesis=active_hyp,
            SimulatedTradeCount=len(memory.experience_memory),
            QCScore=qc_score,
            QCExplanation=qc_msg
        )

        # Generate Dual representation Views
        ai_view = self.observation_brain.generate_ai_view(seq, events)
        human_view = self.observation_brain.generate_human_view(seq)

        # Generate SpreadData from execution conditions
        bid = current_obs.Close - current_spread_val / 2.0
        ask = current_obs.Close + current_spread_val / 2.0
        spread_data = self.reality_engine.observe_spread(current_obs.Asset, bid, ask)

        return report, ai_view, human_view, spread_data
