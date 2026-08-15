# ERROR_STATES.md — Error States

This document details the visual layouts and behaviors of system error pages, error toasts, and fallback mechanisms.

---

## 🚫 Custom 503 Service Unavailable Landing Page

If the core python runtime windows service (`TradeYar-AI`) stops or IIS fails to route to local port 8000, IIS reverse proxy configuration (`scripts/setup_iis_reverse_proxy.ps1`) automatically serves a bilingual custom `503.html` landing page rather than a generic blank IIS page.

### Layout Spec for `503.html`:
- **Theme:** High-contrast dark theme (Background: `#0a0e17`, Card: `#101622`).
- **Accent:** Pulsating red alert icon.
- **Copy (Bilingual - English and Persian):**
  - **EN:** "TradeYar AI System Maintenance. The platform is currently performing a planned software upgrade or SRE diagnostic cycle. Real-time connections are temporarily suspended to protect virtual positions. Service will resume shortly."
  - **FA:** "سیستم ترید‌یار در حال به‌روزرسانی یا تعمیرات است. پلتفرم در حال حاضر در حال ارتقاء نرم‌افزاری یا فرآیندهای عیب‌یابی SRE است. ارتباطات زنده برای محافظت از پوزیشن‌های مجازی موقتاً به حالت تعلیق درآمده‌اند. سرویس به زودی در دسترس خواهد بود."

---

## 🚦 Internal Error Routing States

### 1. 404 Not Found Page
- **Triggers:** Router fails to match any URL inside the active shell layouts.
- **Visuals:** Dark starry backdrop with a floating geometric grid.
- **Interaction:** Single-click secondary button to redirect the user to their respective shell base path (e.g. redirects back to `/dashboard` if logged in, or `/` if guest).

### 2. 403 Forbidden Access Page
- **Triggers:** A standard USER role tries to load the SRE administrative panel at `/admin`.
- **Visuals:** Red neon bordered card with an interactive warning padlock.
- **Interactive Copy:** "Unauthorized SRE Zone. Administrative credentials are required to modify system limits or inspect active memory files. Your attempt has been recorded in the security log."

---

## 🔔 Form & API Error Toast Notifications

For inline API errors (e.g., failed registration validation, invalid password, or exceeded support query limits), display toast notifications.

```
┌───────────────────────────────────────────────┐
│ 🔴 API ERROR (400 Bad Request)              ✖ │
├───────────────────────────────────────────────┤
│ The password must contain at least 8 characters│
│ and one uppercase letter.                     │
└───────────────────────────────────────────────┘
```

- **Placement:** Top-right on desktop, full-width top header on mobile.
- **Timeout:** Auto-dismisses after exactly `5000ms`.
- **Accessibility:** Readable by screen-readers via `role="alert"` wrapper attributes.
