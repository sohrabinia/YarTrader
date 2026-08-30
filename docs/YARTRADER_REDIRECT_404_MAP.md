# YARTRADER — REDIRECT & 404 POLICY MAP

## Permanent 301 Redirects & 404 Handling Policies

### 1. Permanent Redirect Rules (301)
- **Host Normalization**: Non-canonical hosts (`http://yartrader.com`, `https://www.yartrader.com`) redirect with HTTP 301 to `https://yartrader.com`.
- **Protocol Enforcement**: HTTP requests with `X-Forwarded-Proto: http` receive HTTP 301 redirect to HTTPS.
- **Unprefixed Locale Fallback**: Requests to `/features`, `/pricing`, `/guide`, `/faq`, `/blog` resolve via client SPA router to `/fa/features`, `/fa/pricing`, etc.

### 2. 404 Response Policy
- **Invalid Locale or Subpath**: Requests to invalid locales or unknown public subpaths (e.g. `/fa/nonexistent`, `/de`) return HTTP 404 with a localized 404 HTML body and `<meta name="robots" content="noindex">`.
- **API Endpoints**: Unknown `/api/*` endpoints return JSON `{"detail":"Not Found"}` with HTTP 404 status.
