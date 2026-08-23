from src.Infrastructure.Configuration.environment import EnvironmentType, get_current_environment
from src.Infrastructure.Configuration.config import ConfigurationManager
from src.Infrastructure.DI.container import DIContainer, container_instance

# Interfaces
from src.Data.MarketData.Interfaces.interfaces import IMarketDataProvider
from src.Research.MarketAnalysis.Interfaces.interfaces import IResearchEngine, IFractalEngine
from src.Strategy.Interfaces.interfaces import IStrategyEvaluator
from src.Risk.Interfaces.interfaces import IRiskEngine
from src.Decision.Interfaces.interfaces import IDecisionEngine
from src.Learning.Interfaces.interfaces import ILearningEngine

# Concrete classes
from src.Data.MarketData.Providers.providers import MetaTrader5Provider, ExchangeProvider
from src.Research.MarketAnalysis.Services.services import ResearchProcessor
from src.Research.Brain.fractal_engine import FractalEngine
from src.Strategy.Evaluation.evaluation import StrategyEvaluator
from src.Risk.Services.services import RiskAnalyzer
from src.Decision.Intelligence.engine import DecisionEngine as AdvancedDecisionEngine
from src.Learning.Services.services import LearningProcessor

def register_services(container: DIContainer = container_instance, environment: EnvironmentType = None) -> None:
    """Registers environment-specific dependencies in the DI Container."""
    env = environment or ConfigurationManager.get_active_environment()

    # Clear previous registrations first
    container.clear()

    # Generic Singleton bindings (reused across all envs)
    container.register_singleton(IStrategyEvaluator, StrategyEvaluator)
    container.register_singleton(IRiskEngine, RiskAnalyzer)
    container.register_singleton(IDecisionEngine, AdvancedDecisionEngine)
    container.register_singleton(ILearningEngine, LearningProcessor)
    container.register_singleton(IFractalEngine, FractalEngine)

    # Environment-specific registrations
    if env == EnvironmentType.DEVELOPMENT:
        # Development environment maps simple/mock variants
        container.register_singleton(IMarketDataProvider, MetaTrader5Provider)
        container.register_singleton(IResearchEngine, ResearchProcessor)

    elif env == EnvironmentType.TEST:
        # Test environment maps mock variants with fast execution
        container.register_singleton(IMarketDataProvider, MetaTrader5Provider)
        container.register_singleton(IResearchEngine, ResearchProcessor)

    elif env == EnvironmentType.SIMULATION:
        # Simulation environment maps rich simulators
        container.register_singleton(IMarketDataProvider, ExchangeProvider)
        container.register_singleton(IResearchEngine, ResearchProcessor)

    elif env == EnvironmentType.PRODUCTION:
        # Production environment uses robust primary implementations
        container.register_singleton(IMarketDataProvider, MetaTrader5Provider)
        container.register_singleton(IResearchEngine, ResearchProcessor)

    else:
        # Default fallback
        container.register_singleton(IMarketDataProvider, MetaTrader5Provider)
        container.register_singleton(IResearchEngine, ResearchProcessor)
