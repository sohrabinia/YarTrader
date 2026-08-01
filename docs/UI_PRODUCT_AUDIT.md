# TradeYar AI — UI Product Audit

As part of the v3.2 release transition and frontend observatory upgrade, this audit reviews the current state of the product interface and its coupling to the underlying intelligence and SRE backend endpoints.

---

## 1. Frontend Architecture
The user interface is structured as a high-fidelity, highly optimized Single Page Application (SPA) served directly as an HTML/JS/CSS template by the FastAPI server in `src/Application/Services/web_dashboard.py` at `/` and `/dashboard` endpoints.
- **Framework & Libraries**: Raw HTML5/ES6, Tailwind CSS class stylings, custom CSS stylesheets for smooth transition effects.
- **Client State Management**: Plain vanilla JavaScript using asynchronous `fetch` calls and reactive DOM bindings.
- **Localization**: Currently features dual-language translation (Farsi and English) controlled by a dynamic translation lookup dictionary in JavaScript.

---

## 2. Current Pages & Routing
There is a single administrative route `/dashboard` (and its root alias `/`) rendering the single-page application.
- All tabs and views (System Validation Center, Live Market Research, Cognitive Brain Console, Shadow Position Performance) are mapped dynamically within the client-side SPA.
- Backend routing is fully defined in `src/Application/Services/web_dashboard.py` utilizing FastAPI router decorators.

---

## 3. API Connections & Endpoints
The SPA connects to the following active live production APIs:
- `GET /api/validation/status`: Returns current test execution status, component, and log streams.
- `GET /api/validation/history`: Returns historical acceptance run ratios and readiness scores.
- `GET /api/research/current` / `GET /api/research/latest`: Returns latest XAUUSD market analysis snapshots.
- `GET /api/intelligence/status`: Dynamic intelligence brain memory counts.
- `GET /api/intelligence/explain/{decision_id}`: Semantic explanation answers.
- `GET /api/intelligence/learning-report`: Memory-system learning statistics.
- `GET /api/shadow/metrics`: Shadow Trading positions and wallet metrics.
- `GET /health` & `GET /api/v1/health`: Detailed subsystem diagnostics.

---

## 4. Mock Data Locations & Snapshots
- Replay session metadata (`_mock_replay_session`) resides directly in `web_dashboard.py`, acting as a fallback for training statistics.
- Static diagnostic indicators reside in the initialization phase and the default template states.

---

## 5. Missing Product Modules
The following key modules are required for the v3.2 product experience layer:
1. **RTL-Compliant Quad-Language Localization**: Addition of Arabic (ar) and Turkish (tr) languages alongside Farsi and English.
2. **Interactive Floating Chatbot Widget**: An expandable assistant widget supporting cognitive explaining and position analytics without active trading capability.
3. **Research Blog / Knowledge Center**: Clean, responsive layout for analytical market articles and report cards.
4. **AI Content Research Generator**: Controlled governance pipeline for automatic draft generation and human review before publication.

---

*Compiled by Jules, Technical Director*
