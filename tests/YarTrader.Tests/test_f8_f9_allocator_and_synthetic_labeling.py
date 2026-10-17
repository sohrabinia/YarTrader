from scripts.run_phase_2_1_experiment import SYNTHETIC_EVIDENCE
from scripts.run_v1_2_reality_audit import SYNTHETIC_AUDIT_METADATA


def test_phase_2_1_outputs_are_explicitly_non_empirical():
    assert SYNTHETIC_EVIDENCE["synthetic_data"] is True
    assert SYNTHETIC_EVIDENCE["market_data_is_real"] is False
    assert SYNTHETIC_EVIDENCE["evidence_grade"] == "SYNTHETIC_PIPELINE_ONLY"
    assert SYNTHETIC_EVIDENCE["edge_claim_allowed"] is False
    assert "not evidence" in SYNTHETIC_EVIDENCE["interpretation"]


def test_randomized_reality_audit_cannot_claim_a_real_market_edge():
    assert SYNTHETIC_AUDIT_METADATA["synthetic_data"] is True
    assert SYNTHETIC_AUDIT_METADATA["market_data_is_real"] is False
    assert SYNTHETIC_AUDIT_METADATA["data_source"] == "randomly_generated_synthetic_candles"
    assert SYNTHETIC_AUDIT_METADATA["edge_claim_allowed"] is False
    assert SYNTHETIC_AUDIT_METADATA["metrics_empirically_validated"] is False
    assert SYNTHETIC_AUDIT_METADATA["max_drawdown_metric_is_placeholder"] is True
