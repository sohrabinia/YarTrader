# RG_V3_AI Developer Guide

## 1. Environment & Setup
The platform is designed to compile on **Python 3.12**.

### Dependency Manifest Discovery
Identify package manifests in the project root:
```bash
ls pyproject.toml requirements.txt poetry.lock 2>/dev/null
```

### Installation
Install the project dependencies in editable development mode:
```bash
pip install -e .
```

---

## 2. Core Development Workflow
* **Decoupled Entities**: When creating new models, ensure they are placed in their respective domain directory (e.g. `src/Research/MarketAnalysis/Models/`). Dataclasses should preferably be `frozen=True`.
* **Interface Abstraction**: Implementations must inherit from standard abstract interfaces (found under `Interfaces/` directories).
* **Sequential Supervisor Integration**: Register new analytical capabilities within `IntelligenceSupervisor` sequentially (Research -> Strategy -> Risk -> Validation -> Learning) to integrate them cleanly into the Decision Context.
* **Strict Non-Trading bounds**: Never add trading terminology (`buy_order`, `sell_signal`, etc.) contiguous in your variables, method names, or documentation, as they will trigger false-positives in our active safety checkers.
