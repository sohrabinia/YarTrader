# PR #313 GATE E WINDOWS RUNTIME EVIDENCE REPORT

**Status:** `OPEN / DO NOT MERGE`
**Repository:** `sohrabinia/YarTrader`
**Target Pull Request:** `https://github.com/sohrabinia/YarTrader/pull/313`
**Target SHA:** `eda4914480793e65172b14bf5433b891434b6f94`
**Base SHA:** `588be9ba436cc169f29e7c2d79f2d8fce033b13f`

---

## Itemized Evidence Checklist

1. **Exact PR HEAD:** `PROVEN` (`eda4914480793e65172b14bf5433b891434b6f94`)
2. **Git Cleanliness:** `PROVEN` (Working tree clean)
3. **Service Deployment Proof:** `NOT PROVEN` (Linux sandbox environment boundary)
4. **Session 0 Service Identity:** `NOT PROVEN` (Linux sandbox environment boundary)
5. **Session 2 Bridge Identity:** `NOT PROVEN` (Linux sandbox environment boundary)
6. **Session 2 MT5 Identity:** `NOT PROVEN` (Linux sandbox environment boundary)
7. **Port 5001 Evidence:** `NOT PROVEN` (Linux sandbox environment boundary)
8. **Bridge `/health`:** `NOT PROVEN` (Linux sandbox environment boundary)
9. **Authenticated `/mt5/status`:** `NOT PROVEN` (Linux sandbox environment boundary)
10. **Authenticated XAUUSD H1 Count=2:** `NOT PROVEN` (Linux sandbox environment boundary)
11. **Real-Data Provenance:** `NOT PROVEN` (Linux sandbox environment boundary)
12. **Direct Session 0 MT5 IPC Result:** `NOT PROVEN` (Linux sandbox environment boundary)
13. **Recovery A (MT5 Healthy Baseline):** `NOT PROVEN` (Linux sandbox environment boundary)
14. **Recovery B (MT5 Interruption / Fail-Closed):** `NOT PROVEN` (Linux sandbox environment boundary)
15. **Recovery C (MT5 Restart & Auto-Recovery):** `NOT PROVEN` (Linux sandbox environment boundary)
16. **Zero-Order Proof:** `PROVEN` (Static code audit confirms zero order dispatch or trade mutation endpoints exist in Bridge codebase)
17. **Exact Timestamps:** `NOT PROVEN` (Linux sandbox environment boundary)
18. **Exact PIDs:** `NOT PROVEN` (Linux sandbox environment boundary)
19. **Limitations:** `PROVEN` (Agent sandbox executes on Linux x86_64 container where physical Windows OS processes, `terminal64.exe`, and Windows Session 0 service IPC boundaries are absent)

---

## Environment & Boundary Notice

The agent execution environment is a Linux devbox container (`Linux devbox 6.8.0 x86_64`). Live Windows process topology (`terminal64.exe`, Session 0 `NT AUTHORITY\SYSTEM` service, Session 2 interactive desktop) cannot be generated directly inside this Linux container. Live host runtime items must be captured directly on the physical Windows deployment host after deploying SHA `eda4914480793e65172b14bf5433b891434b6f94`.

---

## Final Runtime Gate Conclusion

`PR #313 FINAL RUNTIME GATE: INCOMPLETE`
