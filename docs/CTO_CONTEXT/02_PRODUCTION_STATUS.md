# 02 - Production Runtime & Host Deployment Status

## Production Infrastructure Overview
* **Domain**: `https://yartrader.com`
* **Host Platform**: Native Windows Server 2022
* **Service Manager**: NSSM (Non-Sucking Service Manager)
* **Service Name**: `YarTrader Production Runtime Service`
* **Runtime Python Environment**: Python 3.12 (Isolated venv)
* **Frontend Static Hosting**: Production Vite build serving from `trader-terminal/dist`

## Port Allocation Matrix
| Service | Internal Port | Protocol | Binding | Endpoint / Purpose |
| :--- | :--- | :--- | :--- | :--- |
| **YarTrader Backend API** | `8000` | HTTP/REST | `127.0.0.1` | `/v1/health`, `/api/execution/plans`, `/api/admin/operator` |
| **YarOperator Internal Runtime** | `8080` | HTTP/REST | `127.0.0.1` | Internal Operator Agent API (`YAROPERATOR_RUNTIME_URL`) |
| **Web Dashboard / Frontend SPA** | `80` / `443` | HTTP/HTTPS | `0.0.0.0` | Production UI with HTML5 `BrowserRouter` (`/{lang}/...`) |

## Operational Environment Requirements
* `GOOGLE_CLIENT_ID`: Mandatory for Google OIDC customer authentication. Must be loaded into the NSSM runtime environment.
* `OPERATOR_SERVER_SECRET`: Internal secret key authorizing YarTrader backend proxy to communicate with YarOperator runtime at `http://127.0.0.1:8080`.
* `LIVE_TRADING_ENABLED`: Hard-locked to `False`. Real account logins (`is_real = True`) are rejected immediately by `DemoExecutionGate`.
