# Evidence Traceability Design

## 1. Traceability Map
The mapping flow guarantees full structural traceability:
```text
Answer -> Evidence IDs -> Memory Records -> Validation Status
```

---

## 2. Evidence Fields
Every analytical response must include:
- **Evidence Count**: Quantity of matched historical samples.
- **Data Coverage**: Timeframes and periods scanned.
- **Confidence Source**: Basis of the scoring (e.g. pattern similarity odds).
- **Validation Level**: Whether the reasoning is `PENDING`, `TESTING`, `CONFIRMED`, or `REJECTED`.
- **Unknown Factors**: Volatilities, gaps, or structural details that are currently untested.
