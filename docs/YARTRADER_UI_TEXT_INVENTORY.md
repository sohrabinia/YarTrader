# YarTrader Frontend Complete UI Text Inventory v1.0

**Date:** August 23, 2026
**Author:** Jules — Lead Systems & Frontend Engineer
**Scope:** Complete inventory of all visible UI text strings in `trader-terminal` across Navigation, Dashboard, Cards, Buttons, Forms, Tables, Charts, Notifications, Empty states, Error messages, Auth pages, Admin pages, Settings, Billing, and Wallet.

---

## 1. Global Navigation & Layout Strings

| Location | Current Text | Language | Usage Context | Recommended Text | Recommendation Rationale |
| :--- | :--- | :---: | :--- | :--- | :--- |
| **Sidebar Menu** | `تضمین آنلاین` | `fa` | System status badge | **پایدار / آنلاین** | More accurate status description. |
| **Sidebar Menu** | `سیگنال‌های معاملاتی` | `fa` | Signals route link | **بازار و بینش‌های بازار** | Eliminates retail signal-selling connotation. |
| **Sidebar Menu** | `ترمینال معامله` | `fa` | Dashboard route link | **خانه هوشمند** | Represents the Autonomous Command Center. |
| **Sidebar Menu** | `حالت زنده` | `fa` | Live route link | **حالت زنده (ایمن / مسدود)** | Explicitly clarifies fail-closed SRE safety state. |
| **Header** | `کد کاربری` | `fa` | User profile badge | **حساب کاربری** | Professional user identity label. |

---

## 2. Dashboard & Intelligence Cards

| Location | Current Text | Language | Usage Context | Recommended Text | Recommendation Rationale |
| :--- | :--- | :---: | :--- | :--- | :--- |
| **Dashboard** | `پستور بازار` | `fa` | Signal posture label | **وضعیت ساختار بازار** | Precise market structure posture terminology. |
| **Dashboard** | `تخمین هوش` | `fa` | Inference rationale | **تحلیل و شواهد هوش** | Indicates quantitative rationale. |
| **Dashboard** | `نرخ بازدهی محاسباتی` | `fa` | Compounding yield | **نرخ سود مرکب محاسباتی** | Accurate compounding yield term. |
| **Execution Intel**| `برنامه پیشنهادی` | `fa` | Advisory trade plan | **طرح معامله تجویزی** | Institutional advisory plan terminology. |
| **Execution Intel**| `حد ضرر` | `fa` | Stop loss level | **سطح ابطال تحلیل (SL)** | Clarifies invalidation level function. |
| **Execution Intel**| `حد سود` | `fa` | Take profit level | **سطح هدف معامله (TP)** | Institutional target zone terminology. |

---

## 3. Trading Modes & Position Tables

| Location | Current Text | Language | Usage Context | Recommended Text | Recommendation Rationale |
| :--- | :--- | :---: | :--- | :--- | :--- |
| **Backtest** | `وضعیت نشتی` | `fa` | Leakage audit | **ارزیابی عدم جابجایی زمان (Leakage)** | Explains look-ahead bias audit status clearly. |
| **Backtest** | `تعداد نمونه` | `fa` | Trade count | **حجم نمونه (N)** | Indicates statistical sample size. |
| **Demo Trading** | `سرور دمو` | `fa` | Broker server status | **سرور معامله آزمایشی (Demo)** | Standardized MT5 demo server term. |
| **Shadow Trading** | `حساب فرضی` | `fa` | Virtual paper account | **حساب سرمایه مجازی (Paper)** | Canonical paper execution terminology. |
| **Live Gate** | `خطر معامله زنده` | `fa` | Hard-blocked banner | **حالت زنده غیرفعال است (محدودیت ایمنی SRE)** | Clear SRE safety gate explanation. |

---

## 4. Notifications, Errors & Empty States

| Location | Current Text | Language | Usage Context | Recommended Text | Recommendation Rationale |
| :--- | :--- | :---: | :--- | :--- | :--- |
| **Signals Feed** | `هیچ سیگنالی نیست` | `fa` | Empty signals grid | **هیچ چیدمانی شرایط ارزیابی را احراز نکرده است** | Explains *why* grid is empty. |
| **Backend Error** | `خطای سرور` | `fa` | Connection failed | **ارتباط با سرور برقرار نشد. داده‌های نمایش‌داده‌شده آزمایشی هستند** | Gives user context and next step. |
| **Auth Error** | `ورود ناموفق` | `fa` | Login failure | **پست الکترونیک یا رمز عبور اشتباه است. لطفاً دوباره تلاش کنید** | Answers "What happened?" and "What to do next?". |

---

*Text Inventory certified by Jules — Lead Systems & Frontend Engineer.*
*YarTrader Autonomous Financial Intelligence Platform.*
