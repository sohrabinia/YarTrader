import hashlib
import json
from datetime import datetime, timezone
from typing import Dict, Any

class ExperimentProvenance:
    """
    Immutable experiment provenance recorder for YarTrader Research Optimization.
    Captures complete reproducibility details (commit SHA, dataset hash, config hash, split ratios, metrics, objective score).
    """
    @staticmethod
    def create_provenance_record(
        experiment_id: str,
        commit_sha: str,
        symbol: str,
        timeframe: str,
        dataset_hash: str,
        split_definition: Dict[str, float],
        configuration: Dict[str, Any],
        metrics: Dict[str, Any],
        objective_score: float,
        overfitting_status: str
    ) -> Dict[str, Any]:
        config_hash = hashlib.md5(json.dumps(configuration, sort_keys=True).encode("utf-8")).hexdigest()[:12]

        return {
            "experiment_id": experiment_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "git_commit_sha": commit_sha,
            "symbol": symbol.upper(),
            "timeframe": timeframe,
            "dataset_hash": dataset_hash,
            "split_definition": split_definition,
            "parameter_configuration": configuration,
            "parameter_hash": config_hash,
            "metrics": metrics,
            "objective_score": objective_score,
            "overfitting_status": overfitting_status,
            "reproducibility_token": f"R-{commit_sha[:8]}-{dataset_hash}-{config_hash}"
        }
