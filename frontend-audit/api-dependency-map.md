# api-dependency-map.md

## API Dependency Map

Tracks frontend API consumer connections and the backend endpoints that satisfy them.

```
[Frontend SPA Shell]
         ├── (GET /health) ──────────────→ [SRE Liveness Probe]
         ├── (GET /api/v1/health) ───────→ [SRE Detailed Diagnostics]
         ├── (GET /api/public/metrics) ──→ [Telemetry / Counters]
         ├── (POST /api/chat/assistant) ─→ [AI Cognitive Chatbot Interface]
         └── (GET /api/shadow/metrics) ──→ [Shadow Trading Telemetry Panel]
```

### 1. Endpoint Protocols
- **REST APIs**: Used for static authentication, locale mapping files JSON fetching, blog reading, and metrics queries.
- **WebSockets**: Used for real-time stream of virtual tick updates and shadow order trigger events, utilizing the standard reconnection parameter specs (reconnect limit of 5, exponential backoff).
- **Static Assets**: Bilingual sitemaps, JSON-LD schemas, and localization bundles (`/locales/*`) are fetched via standard HTTP caching headers.
