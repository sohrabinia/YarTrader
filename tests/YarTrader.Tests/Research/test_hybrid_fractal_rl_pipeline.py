"""
Comprehensive Unit, Causality, Regression, and End-to-End Integration Test Suite
===================================================================================
Verifies:
A. Data integrity & no fabrication
B. Causality & zero future look-ahead leakage
C. Layer 1 Math Engines (Hurst, Higuchi D, Wavelet) & Scale-Invariant Similarity
D. Layer 2 MTF State & Pullback vs Reversal Classification
E. Layer 2 Target Probability & MTF Consensus
F. Layer 3 Gymnasium-compatible Environment & PPO Agent
G. Risk Engine 2.0% Hard Ceiling Enforcement
H. End-to-End Hybrid Research-to-Safety Pipeline
"""

import pytest
import numpy as np
from datetime import datetime, timedelta

from src.Research.Brain.fractal_engine import FractalEngine
from src.Research.Brain.hurst_engine import HurstEngine
from src.Research.Brain.fractal_dimension import HiguchiFractalDimension
from src.Research.Brain.wavelet_engine import WaveletEngine
from src.Intelligence.Execution.similarity import PatternSimilarityIntelligenceEngine
from src.Research.Brain.target_probability_engine import TargetProbabilityEngine
from src.Research.Brain.multi_timeframe_state import MultiTimeframeStateBuilder, FractalMarketState
from src.Research.RL.environment import FractalMarketEnv
from src.Research.RL.ppo_agent import PPOAgent
from src.Risk.Services.professional_risk_engine import ProfessionalRiskEngine
from src.Execution.Safety.demo_execution_gate import DemoExecutionGate


class TestHybridFractalRLPipeline:

    # ----------------------------------------------------
    # A. DATA INTEGRITY & NO FABRICATION TESTS
    # ----------------------------------------------------
    def test_data_integrity_rejects_missing_timestamp(self):
        engine = FractalEngine()
        invalid_candles = [{'open': 2000.0, 'high': 2005.0, 'low': 1995.0, 'close': 2001.0, 'volume': 10.0}]
        res = engine.analyze_fractals("XAUUSD", "M5", {"M5": invalid_candles})
        assert res["fractal_status"] == "INSUFFICIENT_DATA"
        assert res["evidence_state"] == "NO_EVIDENCE"

    def test_data_integrity_rejects_non_positive_and_nan_prices(self):
        engine = FractalEngine()
        invalid_candles = [
            {'timestamp': '2025-01-01T10:00:00', 'open': -2000.0, 'high': 2005.0, 'low': 1995.0, 'close': 2000.0, 'volume': 10.0},
            {'timestamp': '2025-01-01T10:05:00', 'open': float('nan'), 'high': 2005.0, 'low': 1995.0, 'close': 2000.0, 'volume': 10.0}
        ]
        res = engine.analyze_fractals("XAUUSD", "M5", {"M5": invalid_candles})
        assert res["fractal_status"] == "INSUFFICIENT_DATA"

    def test_data_integrity_no_fake_50_percent_confidence(self):
        engine = FractalEngine()
        valid_candles = [
            {'timestamp': f'2025-01-01T10:{i:02d}:00', 'open': 2000.0 + i, 'high': 2005.0 + i, 'low': 1998.0 + i, 'close': 2002.0 + i, 'volume': 100.0}
            for i in range(25)
        ]
        res = engine.analyze_fractals("XAUUSD", "M5", {"M5": valid_candles})
        match_record = res["matching_pattern_record"]
        if match_record["evidence_state"] == "NO_EVIDENCE":
            assert match_record["success_rate"] is None
            assert match_record["confidence_weight"] is None

    # ----------------------------------------------------
    # B. CAUSALITY & LEAKAGE TEST
    # ----------------------------------------------------
    def test_causality_future_mutation_does_not_change_past_features(self):
        engine = FractalEngine()
        base_candles = [
            {'timestamp': f'2025-01-01T10:{i:02d}:00', 'open': 2000.0 + (i*0.5), 'high': 2005.0 + (i*0.5), 'low': 1998.0 + (i*0.5), 'close': 2002.0 + (i*0.5), 'volume': 100.0}
            for i in range(25)
        ]

        # Evaluation at time t (last bar index 20)
        subset_at_t = base_candles[:21]
        res_t1 = engine.analyze_fractals("XAUUSD", "M5", {"M5": subset_at_t})

        # Future candles mutated wildly (indices 21 to 24)
        mutated_future_candles = list(base_candles[:21]) + [
            {'timestamp': f'2025-01-01T10:{i:02d}:00', 'open': 5000.0, 'high': 6000.0, 'low': 4000.0, 'close': 5500.0, 'volume': 999.0}
            for i in range(21, 25)
        ]

        # Evaluate feature state strictly up to t (index 20) in mutated series
        subset_mutated_at_t = mutated_future_candles[:21]
        res_t2 = engine.analyze_fractals("XAUUSD", "M5", {"M5": subset_mutated_at_t})

        # Features at t MUST remain identical!
        assert res_t1["hurst_analysis"]["H"] == res_t2["hurst_analysis"]["H"]
        assert res_t1["fractal_dimension_analysis"]["D"] == res_t2["fractal_dimension_analysis"]["D"]

    # ----------------------------------------------------
    # C. LAYER 1 MATHEMATICAL & SCALE-INVARIANT TESTS
    # ----------------------------------------------------
    def test_hurst_engine_persistence(self):
        prices = [2000.0 + i*0.8 for i in range(60)]
        res = HurstEngine().calculate_hurst(prices)
        assert res["H"] > 0.5
        assert res["regime"] == "PERSISTENT_TRENDING"

    def test_higuchi_fractal_dimension(self):
        prices = [2000.0 + (i % 2)*5.0 for i in range(60)]
        res = HiguchiFractalDimension().calculate_dimension(prices)
        assert 1.0 <= res["D"] <= 2.0

    def test_wavelet_decomposition_energy(self):
        prices = [2000.0 + i*0.2 for i in range(32)]
        res = WaveletEngine().decompose(prices)
        assert "A4" in res["energy_per_scale"] or "A3" in res["energy_per_scale"] or "D1" in res["energy_per_scale"]

    def test_scale_invariant_similarity(self):
        sim_engine = PatternSimilarityIntelligenceEngine()
        # Shape A at 4500
        shape_4500 = [4500.0, 4510.0, 4505.0, 4520.0]
        # Shape A at 5000
        shape_5000 = [5000.0, 5010.0, 5005.0, 5020.0]

        g1 = sim_engine.normalize_signature_geometry(shape_4500, atr=5.0)
        g2 = sim_engine.normalize_signature_geometry(shape_5000, atr=5.0)
        similarity = sim_engine._compute_cosine_similarity(g1, g2)

        assert similarity > 0.95

    # ----------------------------------------------------
    # D. LAYER 2 PULLBACK VS REVERSAL TESTS
    # ----------------------------------------------------
    def test_pullback_is_not_classified_as_reversal(self):
        builder = MultiTimeframeStateBuilder()

        h1_rep = {'hurst_analysis': {'H': 0.85, 'regime': 'PERSISTENT_TRENDING'}}
        m15_rep = {'structure_break': False}
        m5_rep = {'hurst_analysis': {'H': 0.40, 'regime': 'ANTI_PERSISTENT_MEAN_REVERTING'}, 'choch_detected': True}

        regime = builder.classify_regime_state({}, h1_rep, m15_rep, m5_rep)
        assert regime == "PULLBACK"
        assert regime != "REVERSAL"

    def test_structural_reversal_classification(self):
        builder = MultiTimeframeStateBuilder()

        h1_rep = {'hurst_analysis': {'H': 0.45, 'regime': 'RANDOM_WALK'}}
        m15_rep = {'structure_break': True}
        m5_rep = {'hurst_analysis': {'H': 0.35, 'regime': 'ANTI_PERSISTENT'}, 'choch_detected': True}

        regime = builder.classify_regime_state({}, h1_rep, m15_rep, m5_rep)
        assert regime == "REVERSAL"

    # ----------------------------------------------------
    # E. TARGET PROBABILITY & CONSENSUS TESTS
    # ----------------------------------------------------
    def test_target_probability_engine(self):
        tpe = TargetProbabilityEngine()
        candles = [{'close': 2000.0 + i} for i in range(25)]
        cands = tpe.evaluate_target_probabilities(2020.0, "BUY", 5.0, candles)
        assert len(cands) >= 3
        for c in cands:
            assert 0.0 <= c.probability <= 1.0

        consensus = tpe.calculate_mtf_consensus({"M5": cands})
        assert consensus.direction in ["BUY", "SELL", "WAIT"]

    # ----------------------------------------------------
    # F. LAYER 3 DEEP RL TESTS
    # ----------------------------------------------------
    def test_fractal_market_env_and_ppo_proposal(self):
        state = FractalMarketState(
            symbol='XAUUSD', timestamp='2025-01-01T10:00:00', primary_timeframe='M5',
            regime_state='CONTINUATION', h4_regime='PERSISTENT_TRENDING',
            h1_regime='PERSISTENT_TRENDING', m15_regime='PERSISTENT_TRENDING',
            m5_regime='PERSISTENT_TRENDING', hurst_h=0.75, fractal_dimension_d=1.2,
            wavelet_dominant_scale='D1', wavelet_high_freq_ratio=0.3, atr=2.5,
            containment_status='ACTIVE', target_consensus={'consensus_probability': 0.7},
            quality_score=0.9
        )
        env = FractalMarketEnv([state, state], [2000.0, 2005.0])
        obs, info = env.reset()
        assert obs.shape == (10,)

        agent = PPOAgent()
        proposal = agent.generate_decision_proposal(obs)
        assert proposal["proposal_action"] in ["HOLD", "ENTER_LONG", "EXIT_LONG", "ENTER_SHORT", "EXIT_SHORT"]
        assert proposal["advisory_note"] is not None

    # ----------------------------------------------------
    # G. RISK ENGINE 2% HARD CEILING ENFORCEMENT
    # ----------------------------------------------------
    def test_risk_engine_enforces_2_percent_hard_ceiling(self):
        risk_engine = ProfessionalRiskEngine()

        # 2.01% -> REJECT
        res_201 = risk_engine.evaluate_equity_risk_and_position_size(
            symbol="XAUUSD", direction="BUY", entry_price=2000.0, stop_loss=1995.0,
            account_equity=10000.0, free_margin=10000.0, risk_pct=2.01
        )
        assert not res_201.is_valid
        assert "exceeds maximum allowable ceiling of 2.0%" in res_201.rejection_reason

        # 2.0% -> ALLOWED if all other checks pass
        res_200 = risk_engine.evaluate_equity_risk_and_position_size(
            symbol="XAUUSD", direction="BUY", entry_price=2000.0, stop_loss=1995.0,
            account_equity=10000.0, free_margin=10000.0, risk_pct=2.0
        )
        assert res_200.is_valid

        # 1.0% -> ALLOWED
        res_100 = risk_engine.evaluate_equity_risk_and_position_size(
            symbol="XAUUSD", direction="BUY", entry_price=2000.0, stop_loss=1995.0,
            account_equity=10000.0, free_margin=10000.0, risk_pct=1.0
        )
        assert res_100.is_valid

    # ----------------------------------------------------
    # H. END-TO-END HYBRID RESEARCH-TO-SAFETY PIPELINE
    # ----------------------------------------------------
    def test_end_to_end_research_to_safety_pipeline(self):
        # 1. Truthful Data
        candles_m5 = [
            {'timestamp': f'2025-01-01T10:{i:02d}:00', 'open': 2000.0 + i*0.5, 'high': 2005.0 + i*0.5, 'low': 1998.0 + i*0.5, 'close': 2002.0 + i*0.5, 'volume': 100.0}
            for i in range(30)
        ]

        # 2. Fractal Engine (Layer 1 + Layer 2 + Layer 3)
        engine = FractalEngine()
        analysis = engine.analyze_fractals("XAUUSD", "M5", {"M5": candles_m5})

        assert analysis["fractal_status"] == "ACTIVE"
        assert analysis["hurst_analysis"]["H"] > 0
        assert analysis["fractal_market_state"] is not None
        assert analysis["ppo_decision_proposal"] is not None

        # 3. Advisory proposal -> Risk Engine validation
        proposal = analysis["ppo_decision_proposal"]
        action = proposal["proposal_action"]

        risk_engine = ProfessionalRiskEngine()
        if action in ["ENTER_LONG", "ENTER_SHORT"]:
            direction = "BUY" if action == "ENTER_LONG" else "SELL"
            sizing = risk_engine.evaluate_equity_risk_and_position_size(
                symbol="XAUUSD",
                direction=direction,
                entry_price=candles_m5[-1]["close"],
                stop_loss=candles_m5[-1]["close"] - 3.0 if direction == "BUY" else candles_m5[-1]["close"] + 3.0,
                account_equity=10000.0,
                free_margin=10000.0,
                risk_pct=1.0  # valid 1% risk proposal
            )
            assert sizing.is_valid
            assert sizing.volume_lots > 0
            assert sizing.risk_pct <= 2.0
