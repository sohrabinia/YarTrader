# YarTrader UI Content & Terminology Review v1.0

**Date:** August 23, 2026
**Author:** Jules — Lead Systems & Frontend Engineer
**Scope:** Review of all user-visible text, Persian/English translation quality, institutional financial terminology, and elimination of robotic or misleading wording.

---

## 1. Terminology Corrections & Recommendations

| Location / Context | Current Text | Problem Identified | Recommended Text | Rationale |
| :--- | :--- | :--- | :--- | :--- |
| **Header Navigation** | `سیگنال‌های فروشی` | Retail signal-selling connotation | **بینش‌های بازار** | Reflects quantitative market intelligence insights. |
| **Dashboard Title** | `ترمینال معاملات` | Generic trading terminal phrase | **خانه هوشمند** | Represents the Autonomous Command Center. |
| **Trading Modes** | `معاملات فرضی` | Misleading/inaccurate phrase | **معاملات سایه (Paper Execution)** | Accurate canonical term for paper simulation. |
| **Decision Section** | `پیش‌بینی مصنوعی` | Robotic translation artifact | **هوشمندی تصمیم‌گیری** | Standard institutional AI Decision Intelligence phrase. |
| **Risk Section** | `حد ضرر اتوماتیک` | Incomplete technical description | **هوشمندی و مدیریت ریسک** | Encompasses portfolio heat, drawdown, and SRE risk gates. |
| **Learning Section** | `یادگیری ربات` | Colloquial phrase | **یادگیری مستمر سیستم** | Professional phrase for continuous pattern adaptation. |

---

## 2. Locale File Verification across 4 Languages

* **`fa.json` (Persian):** Primary institutional language, 100% human-translated, Vazirmatn typography, zero-width non-joiners enforced.
* **`en.json` (English):** Institutional fintech terminology, dark theme vocabulary.
* **`tr.json` (Turkish) & `ar.json` (Arabic):** 100% key parity with `fa.json` and `en.json` (161 keys each).

---

*Content Review certified by Jules — Lead Systems & Frontend Engineer.*
*YarTrader Autonomous Financial Intelligence Platform.*
