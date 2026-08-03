# TradeYar AI — React/Vite Migration Status Report

This document reports the final migration status of TradeYar AI's user interface from the embedded inline FastAPI `web_dashboard.py` SPA to a standalone, React-based Single Page Application (SPA) powered by Vite.

---

## 🏛️ Architecture & Serving Strategy

The frontend of TradeYar AI has been cleanly separated from backend Python strings into a modern React component system.

1. **Standalone React Frontend**:
   - Resides under `/trader-terminal`.
   - Built using Vite for ultra-fast, optimized production bundling.
   - Preserves standard `#hash` client-side routing to match existing URLs perfectly and ensure zero backend modifications are needed for page routing.

2. **Backend Static Mounting & Fallback Serving**:
   - FastAPI in `src/Application/Services/web_dashboard.py` mounts the built assets under the `/assets` endpoint.
   - Serving of `index.html` on endpoints `/` and `/dashboard` uses a zero-risk conditional strategy:
     - **Production mode**: If the compiled `trader-terminal/dist/index.html` exists, it is served directly.
     - **Fallback mode**: If the compiled file is missing, it falls back to the original embedded inline HTML string, enabling dual development modes and seamless, incremental testing.

---

## 📂 Folder Structure

The frontend workspace strictly conforms to the `APPLICATION_STRUCTURE.md` design:

```
trader-terminal/
├── package.json               # Frontend dependencies & standard build scripts
├── vite.config.js             # Vite configuration & assets output rules
├── index.html                 # HTML Entrypoint with Vazirmatn font support
└── src/
    ├── main.jsx               # React DOM entry point
    ├── App.jsx                # Multi-shell SPA layout, Routing, and page panels
    ├── assets/
    │   └── globals.css        # Extracted global CSS rules & theme tokens
    ├── core/
    │   └── config.js          # API base & WS base url constants
    ├── store/
    │   └── useAuthStore.js    # Auth local storage helper
    └── services/
        ├── api.js             # Axios-like Fetch wrapper injecting Bearer token
        └── i18n.jsx           # Multilingual context (EN, FA, AR, TR) & RTL/LTR dynamic switcher
```

---

## 🚀 Build & Deployment Process

### 1. Local Development Setup
Inside the `/trader-terminal` directory:
```bash
# Install dependencies
npm install

# Start Vite local development server
npm run dev
```

### 2. Production Build
Inside the `/trader-terminal` directory:
```bash
# Compile and optimize static assets
npm run build
```
This outputs optimized, compressed, and minified bundles under `trader-terminal/dist/`.

### 3. Server Deployment
Once built, starting the FastAPI backend will automatically detect `trader-terminal/dist/index.html` and serve the modern React SPA immediately with static assets mapped to `/assets`.

---

## 🛡️ Security & Performance Audits

1. **Authentication Security**:
   - Token storage persists in `localStorage` as `tradeyar_token`.
   - Automatically injected in headers as `Authorization: Bearer <token>`.
   - Restricted paths are protected via layout-level routing guards.

2. **Performance Optimization**:
   - Fast initial page loading with a single compressed JS bundle (~180 kB).
   - Localizations fetched on-demand from `/locales/{lang}.json` (no duplicated dictionary files).
   - Minimal external dependencies to avoid security bloat.

---

## ⚠️ Known Limitations & Future Improvements
- **Lazy Loading**: Currently all shells load inside `App.jsx`. In future releases, individual route shells can be lazy-loaded using `React.lazy` and `Suspense` to shrink the initial bundle size even further.
- **Unified WebSocket**: WS connections are established contextually. A global React WS provider can be added in the future.
