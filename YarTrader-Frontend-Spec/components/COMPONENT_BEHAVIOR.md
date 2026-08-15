# COMPONENT_BEHAVIOR.md — Component Behavior

This document details the interactive behavior, client-side event loops, and state-machine transitions for primary platform components.

---

## 🔄 Dynamic Language Selector (`#lang-select`)

The language toggle mechanism must perform dynamic DOM injection.

```
[User clicks Language Select]
                │
                ▼
 [Update local storage "lang"]
                │
                ▼
 [Load locales JSON files] ──────► (e.g., locales/fa.json)
                │
                ▼
 [Execute translatePage()] ──────► (Dynamically updates DOM fields with data-i18n tags)
                │
                ▼
 [Set document direction]  ──────► (fa/ar: direction: rtl, en/tr: direction: ltr)
```

### Dynamic Localized Logic:
1. **Never Hardcode Text:** All visible copy inside templates must use unique localization tags (e.g., `data-i18n="nav.terminal"`).
2. **Handle Select Sync:** When page is reloaded, read the language cookie/localStorage and set the initial selection of the `#lang-select` element.
3. **Typography Switch:** Setting the language to Persian (`fa`) or Arabic (`ar`) must apply `--font-family-sans: "Vazirmatn", ...` to the root HTML body to preserve perfect letter alignment and prevent static or inverted translations.

---

## 🤖 AI Assistant Chatbot Interactivity

The `AssistantChatbot` (`src/Application/Services/web_dashboard.py` `/api/chat/assistant`) operates as a read-only floating panel in the Terminal shell.

### Behavioral State Machine:
1. **`CLOSED` (Default):** Rendered as a minimized floating neon badge in the bottom-right corner. It features a pulsating blue ring. Clicking it transitions the state to `OPEN`.
2. **`OPEN_IDLE`:** Floating drawer panel slide-in with standard Persian/English system greeting. Main input field is focused.
3. **`SENDING`:** Client submits user question to `/api/chat/assistant`. Input text field is disabled. A loading dots animation (`typing-indicator`) is rendered in the chat bubble.
4. **`STREAMING / RENDERING`:** Stream response characters dynamically or render parsed markdown text. Daily support query counter is decremented.
5. **`LIMIT_EXCEEDED`:** If user exceeds their subscription-tier limit (e.g., USER > 10 queries), disable text entry entirely and display an "Upgrade Subscription Plan" card with payment referral links.

---

## 📉 Virtual Position Manager State Transitions

Virtual trades are monitored via the Shadow Trading Engine. The UI must represent these states exactly:

| State | Visual Indicator | Interaction Actions Available | Next Expected State |
| :--- | :--- | :--- | :--- |
| **`OPEN`** | Active green tag with live updating P&L. | Close trade manually (triggers optimistic status). | `MONITORING` |
| **`MONITORING`** | Continuous update loop comparing MT5 stream ticks to virtual SL/TP. | Hover shows exact tick distance to Stop-Loss. | `CLOSED` |
| **`CLOSED`** | Closed red or green tag with final P&L. | View "Judge Brain" explanation feedback modal. | Static History Log |
