# YarTrader V2 — Route Map & SEO Freeze Specification

**Date:** February 2026
**Status:** FROZEN & PROTECTED
**Supported Production Locales:** `fa` (Persian, RTL), `en` (English, LTR), `tr` (Turkish, LTR), `ar` (Arabic, RTL)

---

## 1. Absolute SEO & Route Protection Directives

1. **URL Preservation:** All existing valid public, authenticated, blog, guide, FAQ, and admin URLs across all 4 production locales are strictly frozen.
2. **Shadow Trading Retirement:** `/{lang}/shadow` is retired from active product navigation and removed from sitemap.xml. Unauthenticated or direct requests return HTTP 410 Gone / 301 Redirect to `/{lang}/dashboard`.
3. **Dynamic Locale Prefix Routing:** Every public route is accessible both un-prefixed (defaulting to Persian `fa` or user preference) and explicitly prefixed with `/{lang}/` where `lang` is in `['fa', 'en', 'tr', 'ar']`.
4. **No Soft 404s:** Unknown public subpaths return a strict HTTP 404 response in API contexts or structured localized fallback in SPA routing.
5. **Static SEO Endpoints:**
   - `/sitemap.xml` -> `application/xml` (lists all canonical 4-locale public URLs)
   - `/robots.txt` -> `text/plain; charset=utf-8` (allows public pages, disallows `/api/`, `/admin/`, `/dashboard/`)

---

## 2. Complete Canonical Public & Authenticated URL Inventory

| Path Pattern | Content / Screen Description | Access Level | Canonical Link Structure | Indexing Status |
| :--- | :--- | :--- | :--- | :--- |
| `/` | Landing Homepage (Institutional Hero, Market Stats) | Public | `https://yartrader.com/fa` | `INDEX, FOLLOW` |
| `/{lang}` | Localized Homepage (`fa`, `en`, `tr`, `ar`) | Public | `https://yartrader.com/{lang}` | `INDEX, FOLLOW` |
| `/{lang}/features` | Cognitive Platform Features | Public | `https://yartrader.com/{lang}/features` | `INDEX, FOLLOW` |
| `/{lang}/pricing` | SaaS Plans | Public | `https://yartrader.com/{lang}/pricing` | `INDEX, FOLLOW` |
| `/{lang}/blog` | Algorithmic Research Blog | Public | `https://yartrader.com/{lang}/blog` | `INDEX, FOLLOW` |
| `/{lang}/guide` | User Guide & Platform Architecture | Public | `https://yartrader.com/{lang}/guide` | `INDEX, FOLLOW` |
| `/{lang}/faq` | Frequently Asked Questions | Public | `https://yartrader.com/{lang}/faq` | `INDEX, FOLLOW` |
| `/{lang}/login` | Account Login | Public | `https://yartrader.com/{lang}/login` | `NOINDEX, NOFOLLOW` |
| `/{lang}/register` | Account Registration | Public | `https://yartrader.com/{lang}/register` | `NOINDEX, NOFOLLOW` |
| `/{lang}/forgot-password` | Password Recovery | Public | `https://yartrader.com/{lang}/forgot-password` | `NOINDEX, NOFOLLOW` |
| `/{lang}/dashboard` | User Financial Intelligence Terminal | Authenticated | `https://yartrader.com/{lang}/dashboard` | `NOINDEX, NOFOLLOW` |
| `/{lang}/backtest` | Backtest Execution Hub | Authenticated | `https://yartrader.com/{lang}/backtest` | `NOINDEX, NOFOLLOW` |
| `/{lang}/demo` | Demo Broker Order Monitor | Authenticated | `https://yartrader.com/{lang}/demo` | `NOINDEX, NOFOLLOW` |
| `/{lang}/shadow` | **RETIRED PRODUCT ROUTE** (301 to Dashboard) | Retired | `https://yartrader.com/{lang}/dashboard` | `NOINDEX, NOFOLLOW` |
| `/{lang}/live` | Live Order Safety Boundary (Fail-Closed) | Authenticated | `https://yartrader.com/{lang}/live` | `NOINDEX, NOFOLLOW` |
| `/{lang}/signals` | Cognitive Signals Feed | Authenticated | `https://yartrader.com/{lang}/signals` | `NOINDEX, NOFOLLOW` |
| `/{lang}/execution-intel` | 5-Stage Execution Cascade | Authenticated | `https://yartrader.com/{lang}/execution-intel` | `NOINDEX, NOFOLLOW` |
| `/{lang}/learning` | Multi-Timeframe Learning Matrix | Authenticated | `https://yartrader.com/{lang}/learning` | `NOINDEX, NOFOLLOW` |
| `/{lang}/admin` | SRE Operational Control Center | Admin RBAC | `https://yartrader.com/{lang}/admin` | `NOINDEX, NOFOLLOW` |

---

## 3. SEO / AEO / BEO Structured Data Verification

- **JSON-LD Schemas:** Embedded in `index.html` and updated dynamically:
  - `Organization`: Name (`YarTrader`), URL (`https://yartrader.com`), Logo, Contact Points.
  - `SoftwareApplication`: Name (`YarTrader`), Application Category (`FinanceApplication`), Operating System (`Windows Server`).
  - `FAQPage`: Structured Q&A items in 4 locales.
- **Hreflang Tags:** Explicitly map alternative language versions:
  ```html
  <link rel="alternate" hreflang="fa" href="https://yartrader.com/fa/" />
  <link rel="alternate" hreflang="en" href="https://yartrader.com/en/" />
  <link rel="alternate" hreflang="tr" href="https://yartrader.com/tr/" />
  <link rel="alternate" hreflang="ar" href="https://yartrader.com/ar/" />
  <link rel="alternate" hreflang="x-default" href="https://yartrader.com/fa/" />
  ```
