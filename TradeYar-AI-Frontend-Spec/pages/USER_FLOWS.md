# USER_FLOWS.md — User Journeys & Onboarding Flows

This document details the step-by-step interactive flows for standard users, analysts, and SRE operators executing primary tasks.

---

## 🚀 Flow 1: New User Onboarding & Subscription Activation

This flow maps how a public visitor converts into an active customer in the Terminal shell.

```
[Visitor lands on /]
        │
        ▼
[Clicks "Pricing" Page] ──► (Sees Free, Pro, Premium tiers with crypto options)
        │
        ▼
[Clicks "Get Started" on PRO]
        │
        ▼
[Fills Register Form] ──► (Enters referral code, chooses PBKDF2 password)
        │
        ▼
[Receives Welcome Email] ──► (Simulated via backend transactional EmailService)
        │
        ▼
[Accesses /dashboard] ──► (First-time walkthrough tour overlay triggers)
```

- **Client Requirement:** If registration fails due to duplicate email or weak password, reload form with inline inline error indicators. Retain the user's input fields (except password) to prevent repetitive typing.

---

## 📈 Flow 2: Multi-Timeframe Analytical Signal Verification

This flow describes how a Trader checks a potential signal using the APES-FIN pipeline details.

```
[Trader loads /dashboard]
        │
        ▼
[Selects Symbol "XAUUSD"] ──► (Matrix loads latest prices across M1 to MN1)
        │
        ▼
[Identifies H4 "Buy Advisory"]
        │
        ▼
[Clicks "Research Info" Tab] ──► (Inspects extracted features & QC checks)
        │
        ▼
[Clicks "Strategy Confidence"] ──► (Views rule-based parameters & backtest reports)
        │
        ▼
[Opens Chatbot Widget] ──► (Asks: "Why is H4 bullish?" -> Receives bilingual explanation)
```

- **Client Requirement:** Transitioning from the unified matrix to a detailed timeframe tab must load cached data instantly. Start the network fetch in the background to update the parameters without blocking the user interface.

---

## 🚨 Flow 3: SRE Incident Response & Worker Restart

This flow maps an SRE Operator's response to an MT5 broker connection dropout.

```
[Operator loads /admin]
        │
        ▼
[WebSocket pushes "mt5_disconnected" event]
        │
        ▼
[Console flashes red neon critical alert]
        │
        ▼
[Operator reviews SRE Audit Timeline] ──► (Sees MT5 status: FAILED, Code 503)
        │
        ▼
[Clicks "Restart Worker" Button] ──► (Issues command to API control router)
        │
        ▼
[Success Toast triggers] ──► (Pulsating green status is restored)
```

- **Client Requirement:** Action buttons on the SRE Admin Panel (such as Restart Worker) must display a loading spinner upon click. Disable all alternative action triggers on the page while the command executes to prevent race conditions or duplicate commands.
