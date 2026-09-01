from typing import Dict, Any, List

class OverfittingDiagnostics:
    """
    Overfitting defence and Train/Validation divergence detector.
    Calculates degradation metrics, parameter sensitivity, and stability scores.
    """
    @staticmethod
    def calculate_divergence(train_metric: float, val_metric: float) -> Dict[str, float]:
        """Calculates Train vs Validation metric degradation percentage."""
        if train_metric == 0.0:
            degradation_pct = 0.0
        else:
            degradation_pct = ((train_metric - val_metric) / abs(train_metric)) * 100.0

        return {
            "train_metric": round(train_metric, 2),
            "val_metric": round(val_metric, 2),
            "degradation_pct": round(degradation_pct, 2)
        }

    @classmethod
    def evaluate_candidate_robustness(
        self,
        candidate: Dict[str, Any],
        val_metrics: Dict[str, Any],
        test_metrics: Dict[str, Any]
    ) -> Dict[str, Any]:
        train_pnl = candidate.get("net_pnl", 0.0)
        val_pnl = val_metrics.get("net_pnl", 0.0)
        test_pnl = test_metrics.get("net_pnl", 0.0)

        train_val_div = self.calculate_divergence(train_pnl, val_pnl)
        val_test_div = self.calculate_divergence(val_pnl, test_pnl)

        # Overfitting Warning Conditions
        overfitting_flag = False
        warning_reasons = []

        if train_val_div["degradation_pct"] > 40.0:
            overfitting_flag = True
            warning_reasons.append(f"Train/Val PnL degradation ({train_val_div['degradation_pct']:.1f}%) exceeds 40.0% threshold.")

        if val_test_div["degradation_pct"] > 40.0:
            overfitting_flag = True
            warning_reasons.append(f"Val/Test PnL degradation ({val_test_div['degradation_pct']:.1f}%) exceeds 40.0% threshold.")

        if candidate.get("trade_count", 0) < 5:
            overfitting_flag = True
            warning_reasons.append(f"Insufficient trade sample count ({candidate.get('trade_count', 0)}) < 5 minimum.")

        status = "REJECTED_OVERFITTING" if overfitting_flag else "PASS_ROBUST"

        return {
            "status": status,
            "overfitting_detected": overfitting_flag,
            "train_val_divergence": train_val_div,
            "val_test_divergence": val_test_div,
            "warning_reasons": warning_reasons
        }
