# IIS static frontend and API routing

Deploy `web.config` to the root of the IIS site serving YarTrader.

- Existing files (including the built `assets/` and `locales/`) are served directly by IIS.
- `/` and non-API client routes use the React SPA entry point; `/api/*`, `/v1/*`, `/health`, `/docs`, and `/openapi.json` continue to the API service.
- YarOperator routes remain isolated on loopback port 3000; the YarTrader API remains on loopback port 8000.
- The explicit 503 rule for runtime control, emergency-stop, runtime-status, and uninstrumented telemetry endpoints is a safety interlock. Remove it only after the API service is running the corresponding fail-closed implementation and a real runtime controller/telemetry source is registered. Do not restart the production trading service as part of a static-site deployment.

The current production site uses this rule while its API service remains on the prior runtime build; this prevents false-success responses until a separately approved runtime-service deployment.
