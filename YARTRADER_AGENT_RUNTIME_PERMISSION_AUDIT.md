# YarTrader Agent Runtime Permission Audit

| Agent Name | Entrypoint File | DB Access | Network Access | Trading Permission | Payment Permission | Wallet Permission | Admin Permission |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Research Worker | `app/workers/research_worker.py` | Research Logs | MT5 Terminal IPC | DEMO ONLY | DENY | DENY | DENY |
| Content Agent | `src/Growth/Agents/ContentAgent.py` | Draft Content | Local File System | DENY | DENY | DENY | DENY |
| News Agent | `src/Growth/Agents/DistributionAgents.py` | News Items | Local File System | DENY | DENY | DENY | DENY |
| SEO Agent | `src/Growth/Agents/SEOAgent.py` | Metadata | Local File System | DENY | DENY | DENY | DENY |
| Security Cost Agent | `src/Growth/Agents/SecurityCostAgents.py` | Audit Metrics | Local File System | DENY | DENY | DENY | DENY |
| Trust Learning Agent| `src/Growth/Agents/TrustLearningAgents.py` | Feedback Logs | Local File System | DENY | DENY | DENY | DENY |
