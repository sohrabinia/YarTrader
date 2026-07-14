# RG_V3_AI Testing Guide

## 1. Running Automated Tests
Run the entire platform test suite (1268+ tests) discoverable via pytest:
```bash
PYTHONPATH=. pytest
```

Or execute discover discoverable unit test cases:
```bash
python -m unittest discover tests
```

---

## 2. Structural Isolation & Verification
- **Mock Adapters**: Decouples testing from external exchanges, guaranteeing database-independent verification.
- **Safety Keyword Audit**: Runs AST-based security checks scanning for contiguous keywords (`order`, `broker`) in session variables, config blocks, and source code.
- **Regression Checks**: Encompasses historical backtesting slices, demo scenarios, shadow mode, and REST endpoints.
