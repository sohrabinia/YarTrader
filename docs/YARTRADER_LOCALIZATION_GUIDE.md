# YarTrader Localization Architecture & UX Writing Guide v1.0

**Date:** August 23, 2026
**Author:** Jules — Lead Systems & Frontend Engineer
**Scope:** Architecture check of frontend localization files (`public/locales/fa.json`, `en.json`, `tr.json`, `ar.json`), dynamic RTL layout rules, UX writing standards, and acceptance criteria.

---

## 1. Frontend Localization Architecture

The YarTrader frontend localization architecture is managed via `I18nProvider` (`src/services/i18n.jsx`):

```
trader-terminal/public/locales/
├── fa.json        # Primary Persian (RTL) dictionary (161 keys)
├── en.json        # Institutional English (LTR) dictionary (161 keys)
├── tr.json        # Turkish (LTR) dictionary (161 keys)
└── ar.json        # Arabic (RTL) dictionary (161 keys)
```

* **100% Key Parity:** All 4 locale JSON files maintain byte-for-byte key parity with zero missing keys.
* **Dynamic RTL Enforcement:**
  ```javascript
  const isRTL = targetLang === 'fa' || targetLang === 'ar';
  document.body.dir = isRTL ? 'rtl' : 'ltr';
  document.body.style.fontFamily = isRTL ? "'Vazirmatn', sans-serif" : "'Segoe UI', Roboto, sans-serif";
  ```

---

## 2. UX Writing Standards: The 3-Question Rule

Every error message, notification, toast alert, and empty state MUST clearly answer 3 fundamental questions:

1. **What happened?** (State the objective event clearly).
2. **Why?** (Provide the technical or business reason).
3. **What should the user do next?** (Offer a clear actionable CTA).

### Examples:

#### Bad UX Message:
> `"Error 500: Failed to fetch"`

#### Good YarTrader UX Message:
> **"ارتباط با سرور برقرار نشد."**
> *علت:* زمان پاسخ‌گویی سرور بیش از حد مجاز طول کشید.
> *اقدام بعدی:* لطفاً اتصال اینترنت خود را بررسی کنید یا کلید «تلاش مجدد 🔄» را فشار دهید.

#### Bad Empty State:
> `"No signals found"`

#### Good YarTrader UX Message:
> **"هیچ چیدمانی شرایط ارزیابی را احراز نکرده است."**
> *علت:* تمامی چیدمان‌های فعلی بازار در فیلترهای ارزیابی و مدیریت ریسک رد شده‌اند.
> *اقدام بعدی:* تغییر تایم‌فریم به H4 یا انتخاب نمادهای بیشتر از پنل بالا.

---

## 3. Final Quality Acceptance Criteria

The YarTrader Product Language & Localization Quality Gate PASSES when:

* ✅ Persian UI feels 100% native, professional, and natural with zero machine translation artifacts.
* ✅ English UI reflects institutional fintech rigor.
* ✅ Zero mixed Persian/English sentences in the UI.
* ✅ Canonical terminology dictionary is strictly enforced.
* ✅ 100% key parity maintained across all 4 locales (`fa`, `en`, `tr`, `ar`).
* ✅ Dynamic RTL layout direction works flawlessly across tables, forms, cards, and navigation.
* ✅ All numeric financial data applies `font-variant-numeric: tabular-nums` with `Fira Code` monospace font.

---

*Localization Guide certified by Jules — Lead Systems & Frontend Engineer.*
*YarTrader Autonomous Financial Intelligence Platform.*
