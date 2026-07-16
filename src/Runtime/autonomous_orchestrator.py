from datetime import datetime, timedelta
from typing import Dict, Any

from src.Data.MarketData.Models.models import MarketDataRequest
from src.Data.MarketData.Providers.mt5_provider import MetaTrader5MarketDataProvider
from src.Research.MarketAnalysis.Services.services import FeatureExtractionResearchEngine, ResearchProcessor
from src.Research.MarketAnalysis.Models.models import ResearchRequest
from src.Strategy.Models.models import StrategyCandidate
from src.Strategy.Evaluation.evaluation import StrategyEvaluator
from src.Strategy.strategy_intelligence import StrategyEngine, StrategyLifecycleManager
from src.Strategy.Registry.registry import StrategyRegistry
from src.Risk.Models.models import RiskProfile
from src.Risk.Analysis.risk_management import RiskEngine, RiskPolicy
from src.Decision.Intelligence.models import DecisionIntelligenceContext
from src.Decision.Intelligence.engine import DecisionEngine
from src.Application.Shadow.paper_execution import PaperExecutionEngine, VirtualPortfolio, TradeJournal
from src.Learning.Optimization.learning_intelligence import LearningEngine, PerformanceMemory


class AutonomousOrchestrator:
    """
    Core Autonomous Runtime Orchestrator for TradeYar AI Version 1.0.
    Executes the complete, multi-tiered financial intelligence analytical flow:
    Observe -> Research -> Features -> Strategy -> Decision -> Risk -> Simulated Paper Execution -> Continuous Feedback.
    """

    def __init__(self) -> None:
        # Initialize Ingestion Provider
        self.provider = MetaTrader5MarketDataProvider()

        # Initialize Research Components
        self.base_research = ResearchProcessor()
        self.pipeline_research = FeatureExtractionResearchEngine(data_provider=self.provider, base_engine=self.base_research)

        # Initialize Strategy Components
        self.registry = StrategyRegistry()
        self.evaluator = StrategyEvaluator()
        self.lifecycle_manager = StrategyLifecycleManager(self.registry)
        self.strategy_engine = StrategyEngine(self.evaluator, self.lifecycle_manager)

        # Initialize Risk Components
        self.profile = RiskProfile("Moderate", 1.5, 0.90)
        self.risk_policy = RiskPolicy(self.profile)
        self.risk_engine = RiskEngine(self.risk_policy)

        # Initialize Decision Engine
        self.decision_engine = DecisionEngine()

        # Initialize Paper Trading Components
        self.portfolio = VirtualPortfolio()
        self.journal = TradeJournal()
        self.paper_engine = PaperExecutionEngine(self.portfolio, self.journal)

        # Initialize Learning Loop Components
        self.memory = PerformanceMemory()
        self.learning_engine = LearningEngine(self.memory)

    def execute_complete_flow(self, symbol: str, timeframe: str) -> Dict[str, Any]:
        """
        Executes a single end-to-end analytical intelligence transaction pass.
        Returns the compiled diagnostics and state records of the run.
        """
        # 1. Initialize Connection
        if not self.provider.initialize():
            raise RuntimeError("Orchestrator Error: Failed to initialize MT5 provider.")

        try:
            # 2. Ingest rates & extract features & execute research pipeline
            end_time = datetime.now()
            start_time = end_time - timedelta(days=2)

            research_req = ResearchRequest(
                Asset=symbol,
                StartTime=start_time,
                EndTime=end_time,
                Context={"timeframe": timeframe}
            )
            research_res = self.pipeline_research.analyze_market(research_req)

            # 3. Formulate Strategy Candidate and evaluate suitability
            candidate = StrategyCandidate(
                Id=f"strat-{symbol}",
                Name="Momentum Concept Strategy",
                Description="Evaluates trend indices.",
                ResearchContext=research_res.Findings,
                CreatedAt=datetime.now(),
                EvaluationStatus="Pending"
            )
            # Register strategy and activate it inside lifecycle manager
            from src.Strategy.Models.models import StrategyDefinition
            self.registry.register_strategy(StrategyDefinition(candidate.Id, candidate.Name, "", datetime.now(), "1.0.0", "Approved"))
            self.lifecycle_manager.activate_strategy(candidate.Id)
            strategy_eval = self.strategy_engine.process_candidate(candidate)

            # 4. Enforce Decision Intelligence
            from src.Research.MarketAnalysis.Models.models import MarketInsight
            from src.Research.Engine.models import PatternObservation

            # Form standard DTO Context
            dummy_insight = MarketInsight("Trend", "Standard trend description", 0.90, datetime.now())
            intel_context = DecisionIntelligenceContext(
                ResearchInsights=[dummy_insight],
                PatternObservations=[],
                StrategyEvaluations=[strategy_eval],
                RiskAssessments=[], # assessed downstream
                MarketConditions={"timeframe": timeframe},
                HistoricalEvidence={},
                Metadata={"asset": symbol}
            )

            # Generate decision proposal
            decision_report = self.decision_engine.evaluate_intelligence_context(intel_context)

            # 5. Enforce Risk Sizing & safety limits checks
            target_weights = {symbol: strategy_eval.Score.OverallScore}
            risk_assess = self.risk_engine.assess_allocation(target_weights)
            position_sizes = self.risk_engine.calculate_position_sizing(target_weights)

            # 6. Execute Shadow Paper Simulation Trading if approved
            latest_price = 2000.0 if "XAU" in symbol else 1.1000
            if risk_assess.IsApproved and decision_report.State == "Approved":
                self.paper_engine.process_decision_allocation(
                    symbol=symbol,
                    target_weight=strategy_eval.Score.OverallScore,
                    current_price=latest_price
                )

            # 7. Record to Learning loop Performance Memory
            self.memory.record_decision(decision_report)
            feedback = self.learning_engine.generate_feedback_report()

            return {
                "timestamp": datetime.now().isoformat(),
                "symbol": symbol,
                "timeframe": timeframe,
                "research_confidence": research_res.ConfidenceScore,
                "strategy_score": strategy_eval.Score.OverallScore,
                "decision_state": str(decision_report.State),
                "risk_approved": risk_assess.IsApproved,
                "position_sizing": position_sizes,
                "virtual_balance": self.portfolio.balance,
                "learning_feedback": feedback
            }

        finally:
            self.provider.shutdown()
