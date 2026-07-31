# TradeYar AI — User Experience (UX) Blueprint

This document details the **User Experience (UX) Blueprint** for the TradeYar AI Console, highlighting layout design, bilingual interactions, and conversational user workflows.

## 1. Product Objectives & Target Audience

TradeYar AI serves professional proprietary traders and quantitative analysts. Rather than acting as a black-box trade execution system (which would violate read-only safety rules), TradeYar serves as an **interactive cognitive advisory system**, focusing on explainability, safety, and learning tracking.

## 2. Dynamic Bilingual (RTL/LTR) Workspace

To support both Middle Eastern prop-firms and international quant researchers, the workspace supports continuous bilingual swapping:

* **Default Persian RTL Layout**: Loads by default with RTL orientation, serving optimized `Vazirmatn` Persian web-fonts to ensure absolute visual elegance and readability.
* **English LTR Layout**: Accessible at a single click. Instantly flips the entire dashboard orientation, margins, grid column order, and text fields into a standard LTR layout.
* **Persistent Preferences**: User language selection is preserved inside browser `localStorage` to survive server restarts or page refreshes.

## 3. Interactive UX Workflows

### A. Real-Time Market Polling & Analysis
The top card visualizes continuous, read-only XAUUSD H1 live market research analysis. If MetaTrader5 is disconnected, the system automatically falls back to deterministic simulation, never throwing false-positive errors to the user.

### B. Interactive Conversational Explainability
Users can inspect why the brain opened a trade or skipped a consolidation period:
1. The user clicks on the query button (e.g. `کجا اشتباه کردی؟`).
2. An asynchronous, non-blocking HTTP fetch query targets the versioned API.
3. The response field is updated in real-time with an elegant code syntax template displaying predictions, actual market reality, volatility failures, and lessons stored.

### C. Live Acceptance Validation
Under the validation card, the user can click `اجرای فرآیند تایید نهایی` to trigger automated pytest execution across the 1340+ test cases. Live progress is streamed into an interactive, read-only console window, and detailed validation HTML/Markdown scorecards can be downloaded immediately upon conclusion.
