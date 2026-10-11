"""Long-running DEMO-only worker for YarTrader's Base hierarchy/reaction model."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from src.Execution.Services.autonomous_demo_trader import run_autonomous_demo_trading_loop

if __name__ == "__main__":
    run_autonomous_demo_trading_loop()
