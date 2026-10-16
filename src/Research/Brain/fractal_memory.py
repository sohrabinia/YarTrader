import json
import os
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

MEMORY_FILE = "runtime_logs/fractal_pattern_memory.json"

@dataclass
class FractalPatternRecord:
    pattern_id: str
    timeframe: str
    market_context: str
    frequency: int
    wins: int
    losses: int
    success_rate: float
    confidence_weight: float

class FractalPatternMemory:
    """
    Stores and retrieves self-similar fractal price action patterns across timeframes.
    Updates frequency, outcome, success rate, and confidence weights over time.
    """

    def __init__(self, memory_file: str = MEMORY_FILE) -> None:
        self.memory_file = memory_file
        self.memory: Dict[str, FractalPatternRecord] = {}
        os.makedirs(os.path.dirname(self.memory_file), exist_ok=True)
        self.load_memory()

    def load_memory(self) -> None:
        if os.path.exists(self.memory_file):
            try:
                with open(self.memory_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for k, v in data.items():
                        self.memory[k] = FractalPatternRecord(**v)
                return
            except Exception:
                pass
        # Default initial seed patterns across timeframes
        self._seed_default_patterns()

    def _seed_default_patterns(self) -> None:
        # Fresh installs start without fabricated historical win-rate priors.
        # These are pattern definitions only; confidence remains neutral until
        # genuine broker-reconciled outcomes are recorded.
        default_records = [
            FractalPatternRecord("PAT_LIQUIDITY_SWEEP_REVERSAL", "M15", "TRENDING_UP", 0, 0, 0, 0.0, 0.5),
            FractalPatternRecord("PAT_MSS_BREAKOUT", "H1", "TRENDING_UP", 0, 0, 0, 0.0, 0.5),
            FractalPatternRecord("PAT_RANGE_COMPRESSION_EXPANSION", "H4", "RANGE_BOUND", 0, 0, 0, 0.0, 0.5),
            FractalPatternRecord("PAT_FALSE_BREAKOUT_TRAP", "M5", "RANGE_BOUND", 0, 0, 0, 0.0, 0.5)
        ]
        for rec in default_records:
            self.memory[rec.pattern_id] = rec
        self.save_memory()

    def save_memory(self) -> None:
        with open(self.memory_file, "w", encoding="utf-8") as f:
            json.dump({k: asdict(v) for k, v in self.memory.items()}, f, indent=2)

    def find_matching_pattern(self, pattern_type: str, context: str) -> Optional[FractalPatternRecord]:
        for rec in self.memory.values():
            if pattern_type in rec.pattern_id and (rec.market_context == context or context == "ANY"):
                return rec
        return self.memory.get("PAT_LIQUIDITY_SWEEP_REVERSAL")

    def record_outcome(self, pattern_id: str, is_win: bool) -> FractalPatternRecord:
        if pattern_id not in self.memory:
            record = FractalPatternRecord(pattern_id, "M15", "GENERAL", 1, 1 if is_win else 0, 0 if is_win else 1, 1.0 if is_win else 0.0, 0.5)
            self.memory[pattern_id] = record
        else:
            record = self.memory[pattern_id]
            record.frequency += 1
            if is_win:
                record.wins += 1
            else:
                record.losses += 1
            record.success_rate = round(record.wins / record.frequency, 4)
            # Update confidence weight dynamically using empirical win rate
            record.confidence_weight = round(0.4 + (record.success_rate * 0.5), 4)

        self.save_memory()
        return record
