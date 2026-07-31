# TradeYar AI — Conversation Intelligence Layer

This document details the architecture, design, and implementation of the **TradeYar Conversation Intelligence Layer**, designed to bridge the gap between raw trading machine representations and human traders.

## Overview

Unlike general-purpose conversational LLMs (e.g., ChatGPT), TradeYar Conversation Intelligence relies exclusively on structured, verifiable facts retrieved directly from the Newborn Market Discovery Brain's multi-layered memory structures.

```
                  [Human User Question]
                            │
                            ▼
                [DecisionExplainer Parser]
                            │
                ┌───────────┴───────────┐
                ▼                       ▼
    [Evidence Retrieval]       [Reason Assembly]
    (MarketMemorySystem)     (TradeReasonBuilder)
                │                       │
                └───────────┬───────────┘
                            ▼
                    [Output Formatter]
                    (EvidenceFormatter)
                            │
                            ▼
                  [Human Readable Answer]
```

## Layer Architecture

The layer resides under `src/Intelligence/Explanation/` and features four specialized components:

### 1. `DecisionExplainer`
The central manager acting as the conversational controller. It parses incoming natural-language strings (English or Persian), identifies the query intent, routes the request to appropriate internal builders, and formats the output.

### 2. `TradeReasonBuilder`
Compiles logical reasons for executing trades or waiting on the sidelines, articulating threshold breaches, high-volatility event warnings, and lack of similar historical contexts.

### 3. `EvidenceFormatter`
Standardizes statistical evidence counts, successes, failures, and confidence percentages into clean, bilingual, human-readable templates.

### 4. `LearningSummary`
Structures newly discovered pattern signatures, accuracy scores, prediction errors vs. actual outcomes, and unmapped/unknown market behavior areas.

## Core Question Catalog & Templates

The layer supports both **Persian (FA)** and **English (EN)** for the following five mandatory trader inquiries:

### Q1: Why did you open this trade? (چرا این معامله را باز کردی؟)
Explains the target asset, decision action, matching historical counts, confidence levels, and active risk alerts.
* **Persian Output Template**:
  ```
  تصمیم: خرید طلا (BUY XAUUSD)
  ریسک: رویداد نوسان بالا شناسایی شد

  شواهد: ۸۵۰ نمونه تطبیق تاریخی
  موفق: ۶۲۰
  ناموفق: ۲۳۰
  سطح اطمینان: ۷۲٪
  ```

### Q2: Why didn't you trade? (چرا معامله نکردی؟)
Articulates lack of sufficient matching sequences or low confidence.
* **Persian Output Template**:
  ```
  معامله‌ای انجام نشد.
  دلیل: تنها ۱۴ مورد مشابه یافت شد.
  سطح اطمینان: ۳۸٪
  شواهد ناکافی است.
  ```

### Q3: What did you learn? (چه چیزی یاد گرفتی؟)
Lists newly discovered patterns and general accuracy of recent episodes.
* **Persian Output Template**:
  ```
  الگوی جدید کشف شد: بازگشت طلا پس از آغاز بازار لندن.
  تعداد تکرار: ۳۱۲
  دقت: ۶۹٪
  ```

### Q4: Where did you make a mistake? (کجا اشتباه کردی؟)
Explains discrepancy between the brain's expectation and market reality, documenting lessons learned.
* **Persian Output Template**:
  ```
  پیش‌بینی: ادامه روند (Continuation)
  واقعیت: بازگشت روند (Reversal)
  دلیل شکست: نمونه‌های تاریخی فاقد موارد نوسانی ناشی از اخبار بودند.
  درس جدید ایجاد شد.
  ```

### Q5: What don't you know? (چه چیزی را نمی‌دانی؟)
Exposes low confidence regions or lack of sufficient samples to act safely.
* **Persian Output Template**:
  ```
  دانش ناکافی.
  تنها ۵ نمونه تاریخی وجود دارد.
  سطح اطمینان بسیار پایین است.
  ```
