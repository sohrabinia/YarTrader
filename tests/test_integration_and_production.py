import unittest
import sys
from datetime import datetime
from src.Infrastructure import get_clean_logger, ConfigurationLoader, RGException, ValidationException, ModelValidator
from src.Risk import RiskProfile, RiskAnalyzer, ServiceRiskEvaluator
from src.Decision import DecisionState, DecisionContext, DecisionReason, DecisionEngine
from src.Execution import OrderRequest, OrderResponse, MT5AdapterPlaceholder, GenericBrokerAdapterPlaceholder
from src.Learning import LearningFeedback, PerformanceRecord, ImprovementSuggestion, LearningProcessor

class TestIntegrationAndProduction(unittest.TestCase):
    def test_imports_and_instantiation(self):
        """Phase 10: Import tests for new layers (Phases 5-8)."""
        # Risk Layer
        profile = RiskProfile("Low", 1.0, 0.20)
        self.assertEqual(profile.RiskToleranceLevel, "Low")
        analyzer = RiskAnalyzer()
        assessment = analyzer.analyze_risk({"AAPL": 0.15}, profile)
        self.assertTrue(assessment.IsApproved)

        # Decision Layer
        context = DecisionContext("strat-01", {"AAPL": 0.15}, "Low")
        engine = DecisionEngine()
        result = engine.evaluate_decision(context)
        self.assertEqual(result.State, DecisionState.APPROVED)

        # Execution Layer
        request = OrderRequest("AAPL", "Buy", 10.0, 0.15)
        mt5 = MT5AdapterPlaceholder()
        response = mt5.send_order_to_broker(request)
        self.assertEqual(response.Status, "MockPlaced")

        # Learning Layer
        processor = LearningProcessor()
        feedback = LearningFeedback("dec-001", 0.05, datetime.now())
        processor.process_feedback(feedback)
        suggestions = processor.generate_suggestions()
        self.assertEqual(len(suggestions), 1)
        self.assertEqual(suggestions[0].TargetParameter, "MaxSingleAssetExposure")

    def test_validation_framework(self):
        """Phase 10: Verification of unified validation framework."""
        # 1. Valid positive
        ModelValidator.validate_positive(10.5, "price")
        with self.assertRaises(ValidationException):
            ModelValidator.validate_positive(-1.5, "price")

        # 2. Non-negative
        ModelValidator.validate_non_negative(0.0, "volume")
        with self.assertRaises(ValidationException):
            ModelValidator.validate_non_negative(-0.01, "volume")

        # 3. Weights sum limit
        ModelValidator.validate_weights_sum({"AAPL": 0.40, "MSFT": 0.50}, 1.0, "portfolio")
        with self.assertRaises(ValidationException):
            ModelValidator.validate_weights_sum({"AAPL": 0.80, "MSFT": 0.50}, 1.0, "portfolio")

    def test_configuration_and_logging(self):
        """Phase 10: Infrastructure, config, and logger validation."""
        loader = ConfigurationLoader({"ENV_MODE": "Production"})
        self.assertEqual(loader.get("ENV_MODE"), "Production")
        self.assertEqual(loader.get("NON_EXISTENT", "default"), "default")

        logger = get_clean_logger("RG_V3_TEST")
        self.assertIsNotNone(logger)

    def test_clean_architecture_dependency_direction(self):
        """Phase 9: Strict dependency hierarchy and circular import check."""
        # Verify Core has absolutely zero imports from Data, Research, Strategy, Risk, Decision, etc.
        # We can dynamically inspect modules in sys.modules
        core_module_names = [name for name in sys.modules if name.startswith("src.Core")]
        for name in core_module_names:
            module = sys.modules[name]
            module_dict_keys = list(module.__dict__.keys())
            for key in module_dict_keys:
                import_path = str(module.__dict__[key])
                self.assertNotIn("src.Data", import_path, f"Dependency Violation: Core module '{name}' imports 'src.Data'")
                self.assertNotIn("src.Research", import_path, f"Dependency Violation: Core module '{name}' imports 'src.Research'")
                self.assertNotIn("src.Strategy", import_path, f"Dependency Violation: Core module '{name}' imports 'src.Strategy'")
                self.assertNotIn("src.Risk", import_path, f"Dependency Violation: Core module '{name}' imports 'src.Risk'")
                self.assertNotIn("src.Decision", import_path, f"Dependency Violation: Core module '{name}' imports 'src.Decision'")
                self.assertNotIn("src.Execution", import_path, f"Dependency Violation: Core module '{name}' imports 'src.Execution'")
                self.assertNotIn("src.Learning", import_path, f"Dependency Violation: Core module '{name}' imports 'src.Learning'")
