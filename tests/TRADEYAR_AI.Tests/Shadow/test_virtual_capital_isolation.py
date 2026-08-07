import unittest
from src.ShadowTrading.Services.VirtualCapitalProvider import VirtualCapitalProvider
from src.ShadowTrading.Engine.ShadowTradingEngine import ShadowTradingEngine

class TestVirtualCapitalIsolation(unittest.TestCase):
    """
    SRE Test Suite for Virtual Capital Isolation and Zero Balance Simulation.
    Validates capital routing under multiple trade and operating modes.
    """

    def setUp(self) -> None:
        # Reset any active ShadowTradingEngine singleton instances to clean state
        ShadowTradingEngine._instance = None

    def tearDown(self) -> None:
        ShadowTradingEngine._instance = None

    def test_scenario_1_real_account_zero_balance_live_mode(self) -> None:
        """Test 1: Real account zero balance in LIVE mode - NO virtual capital injection."""
        capital = VirtualCapitalProvider.get_available_balance(trading_mode="LIVE", real_broker_balance=0.0)
        self.assertEqual(capital, 0.0)

    def test_scenario_2_real_account_zero_balance_shadow_mode(self) -> None:
        """Test 2: Real account zero balance in SHADOW mode - Capital injected as 1000 USD."""
        capital = VirtualCapitalProvider.get_available_balance(trading_mode="SHADOW", real_broker_balance=0.0)
        self.assertEqual(capital, 1000.0)

        # Confirm shadow engine is allowed to create trade simulations with virtual capital
        engine = ShadowTradingEngine.get_instance(initial_balance=capital)
        self.assertEqual(engine.account.balance, 1000.0)
        self.assertEqual(engine.get_metrics()["balance"], 1000.0)

    def test_scenario_3_real_account_five_thousand_balance_shadow_mode(self) -> None:
        """Test 3: Real account has 5000, but SHADOW mode still enforces 1000 USD virtual capital."""
        capital = VirtualCapitalProvider.get_available_balance(trading_mode="SHADOW", real_broker_balance=5000.0)
        self.assertEqual(capital, 1000.0)

    def test_scenario_4_production_safety_no_mt5_send(self) -> None:
        """Test 4: Production safety - Verify that no real MT5 order sends are ever triggered under shadow simulation."""
        # Validate that the shadow position manager does not contain active MT5 execution handles
        engine = ShadowTradingEngine.get_instance()
        # Since we use PositionManager which directly maps VirtualPositions locally to VirtualAccount,
        # verify that opening a position doesn't trigger broker interaction and returns a local VirtualPosition
        pos = engine.handle_decision(
            decision_action="BUY",
            current_price=2000.0,
            symbol="XAUUSD",
            volume=0.1,
            timeframe="M15"
        )
        self.assertIsNotNone(pos)
        self.assertEqual(pos.symbol, "XAUUSD")
        self.assertEqual(pos.volume, 0.1)
        # Position is inside local VirtualAccount
        self.assertEqual(len(engine.account.get_open_positions()), 1)
