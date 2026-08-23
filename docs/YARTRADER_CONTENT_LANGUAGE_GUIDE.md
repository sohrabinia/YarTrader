# YarTrader Content Language & Institutional Translation Guide v1.0

**Date:** August 23, 2026
**Author:** Jules — Lead Systems & Frontend Engineer
**Scope:** Canonical financial terminology dictionary, Persian RTL localization standard, human-translation quality rules, and locale file integrity across 4 languages (Fa, En, Tr, Ar).

---

## 1. Quality Standards & Core Principles

YarTrader is an **Autonomous Financial Intelligence Operating System**. All user-facing text, alerts, navigation menus, and AI explanations must reflect institutional financial rigor:

* **Strict Prohibition of Machine Artifacts:** Literal Google Translate outputs or clunky machine phrases (e.g. "معاملات فرضی" or "خرید و فروش سیگنال") are strictly prohibited.
* **Persian RTL First-Class Quality:** Persian (`fa.json`) is the primary institutional language, formatted with `Vazirmatn` font, proper zero-width non-joiner (`‌`), and natural Persian financial vocabulary.
* **Professional Terminology:** Use "بینش‌های بازار" (Market Insights) rather than "سیگنال‌های فروشی" (Signals for Sale), and "هوشمندی تصمیم" (Decision Intelligence) rather than "پیش‌بینی مصنوعی".

---

## 2. Canonical Product Terminology Dictionary

| Concept / English Term | Persian (Fa - Primary) | Arabic (Ar) | Turkish (Tr) | Canonical Context & Rules |
| :--- | :--- | :--- | :--- | :--- |
| **Autonomous Command Center** | **خانه هوشمند** | **مركز القيادة الذاتي** | **Otonom Komuta Merkezi** | Main dashboard route header (`/dashboard`). |
| **Market Intelligence & Insights** | **بازار و بینش‌های بازار** | **رؤى واستخبارات السوق** | **Piyasa İstihbaratı ve İpuçları** | Avoid "Signals". Represents quantitative insights. |
| **Research Center** | **مرکز تحقیقات بازار** | **مركز البحوث الكمية** | **Piyasa Araştırma Merkezi** | Institutional market research reports. |
| **Fractal Market Intelligence** | **هوش فراکتالی بازار** | **الذكاء الفركتالي للسوق** | **Fraktal Piyasa İstihbaratı** | Multi-scale structural self-similarity analysis. |
| **Regime Analysis** | **تحلیل شرایط و رژیم بازار** | **تحليل نظام السوق** | **Piyasa Rejimi Analizi** | Volatility, trending, and ranging state meter. |
| **Decision Intelligence** | **هوشمندی تصمیم‌گیری** | **ذكاء القرار الاستثماري** | **Karar İstihbaratı** | XAI rationale and 5-stage execution plan. |
| **Risk Intelligence & Control** | **هوشمندی و مدیریت ریسک** | **إدارة وذكاء المخاطر** | **Risk İstihbaratı ve Yönetimi** | Portfolio heat, risk budget, emergency stop. |
| **Demo Execution Environment** | **محیط معامله آزمایشی** | **بيئة التداول التجريبية** | **Demo İşlem Ortamı** | MT5 Demo account #52961173 execution center. |
| **Paper Shadow Trading** | **معاملات سایه (Paper Execution)** | **تداول الظل الافتراضي** | **Gölge İşlem Yönetimi** | Virtual capital ($1,000) simulation. |
| **Position Lifecycle** | **چرخه حیات موقعیت معامله** | **دورة حياة الصفقة** | **Pozisyon Yaşam Döngüsü** | 5-phase stepper (`Created → Validated → Opened → Managed → Closed`). |
| **Trade Journal** | **دفتر ثبت و تحلیل معاملات** | **دفتر سجل التداول** | **İşlem Günlüğü ve Günce** | MAE/MFE scatter plot and reflection notes. |
| **Continuous Learning Loop** | **یادگیری مستمر سیستم** | **حلقة التعلم المستمر** | **Sürekli Öğrenme Döngüsü** | Pattern performance matrix and model feedback. |
| **SRE Control Plane** | **مرکز عملیات و پایش سیستم** | **مركز عمليات SRE** | **SRE Operasyon Merkezi** | Admin operations, runtime logs, validation. |
| **Wallet & Ledger Balance** | **کیف پول و صورت‌حساب** | **المحفظة ورصيد دفتر الديون** | **Cüzdan ve Defter Bakiyesi** | User credit balance and ledger transactions. |
| **Subscription & Entitlements** | **مدیریت اشتراک و دسترسی‌ها** | **إدارة الاشتراك والتراخيص** | **Abonelik ve Yetki Yönetimi** | SaaS plan tiers and active entitlements. |

---

## 3. UI Content & Navigation Menu Translation Standard

The 20 main user navigation items in Persian (`fa.json`) are standardized as follows:

```json
{
  "nav_dashboard": "خانه هوشمند",
  "nav_market": "بازار و بینش‌های بازار",
  "nav_research": "تحقیقات بازار",
  "nav_fractal": "هوش فراکتالی بازار",
  "nav_regime": "شرایط و رژیم بازار",
  "nav_decisions": "مرکز تصمیم‌گیری",
  "nav_risk": "مدیریت و کنترل ریسک",
  "nav_demo": "محیط آزمایشی (Demo)",
  "nav_shadow": "معاملات سایه (Paper)",
  "nav_backtest": "آزمایشگاه بک‌تست",
  "nav_positions": "چرخه حیات موقعیت‌ها",
  "nav_journal": "دفتر ثبت معاملات",
  "nav_performance": "گزارش عملکرد و بازدهی",
  "nav_learning": "یادگیری مستمر سیستم",
  "nav_reports": "گزارش‌های قابل دانلود",
  "nav_wallet": "کیف پول و اعتبار",
  "nav_billing": "مدیریت اشتراک",
  "nav_support": "پشتیبانی و تیکت‌ها",
  "nav_profile": "پروفایل کاربری",
  "nav_settings": "تنظیمات ترمینال"
}
```

---

## 4. Quality Verification & Key Parity Rules

* **Key Parity:** Every translation key in `fa.json` MUST exist in `en.json`, `tr.json`, and `ar.json`.
* **Zero Missing Keys:** Fallback logic `t(key)` returns the readable string or key without crashing if missing.
* **Formatting:** Tabular financial numbers and prices MUST use standard Western Arabic numerals (`123,456.78`) formatted with monospace `Fira Code` font to maintain financial column alignment across LTR and RTL layouts.

---

*Content Language Guide certified by Jules — Lead Systems & Frontend Engineer.*
*YarTrader Autonomous Financial Intelligence Platform.*
