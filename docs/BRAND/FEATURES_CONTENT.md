# TradeYar AI — Platform Features & Copy Library
*Document Reference: TY-BRAND-FEAT-03*
*Category: Feature Reframing & Copy Library*

---

## Reframing Features: From Tools to Pillars

We reframe all technical aspects of TradeYar AI's code into four unified intelligence pillars. Each pillar addresses a specific cognitive limitation of manual trading.

---

## Pillar 1: Market Intelligence (Structure & Context)

Manual traders struggle to synthesize multiple horizons concurrently, often missing macro trend traps while chasing micro breakouts. Market Intelligence solves this by establishing strict multi-timeframe structural context.

### Key Capabilities:
1. **Multi-Market Matrix Synchronization:** Continuously tracks up to **30 active symbols** across multiple asset classes (Currencies, Metals, Indices, Crypto) with complete data and memory isolation.
2. **Multi-Horizon Decision Fusion:** Evaluates and aligns price actions across exactly **eight core timeframes** (M1, M5, M15, H1, H4, D1, W1, MN1).

### Interface & Copy Library:
- **Component Copy (Symbol Ticker Card):**
  > **XAUUSD [Gold] — H4 Posture:** `STRUCTURAL_BULLISH` (Consensus Score: 82/100)
- **Timeframe Alignment Grid Copy:**
  - *Micro Horizon (M1, M5):* "Compression breakout confirmed. Local volume-at-price accumulation active."
  - *Short Horizon (M15, H1):* "Support validation sequence initiated. Reaction zone cleared."
  - *Medium Horizon (H4, D1):* "Macro structural bias remains bullish. Key structural reaction zone verified at $2,310."
  - *Macro Horizon (W1, MN1):* "Long-term trend posture maintains structural expansion boundaries."

---

## Pillar 2: Cognitive Intelligence (Recognition & Learning)

Human memory is subjective and prone to recency bias. Cognitive Intelligence implements a rigorous, file-persistent memory system that stores historical patterns, validates them statistically, and updates confidence weights through live outcomes.

### Key Capabilities:
1. **Four-Layered Memory Consolidation:**
   - **Raw Experience:** Captures the immediate metrics of every virtual position (entries, exits, excursions).
   - **Validated Experience:** Sifted by the `StatisticalValidationEngine` to ensure minimum sample sizes.
   - **Pattern Memory:** Extracts generalized, multi-timeframe price-action signatures.
   - **Concept Memory:** Establishes highly reliable trading hypotheses.
2. **The Forgetting/Retention Loop:** Calculates confidence decay based on structural age and pattern failure rates, ensuring the system naturally phases out obsolete market regimes.

### Interface & Copy Library:
- **Component Copy (Learning Stats Panel):**
  > **Cognitive Brain Load Status:** 1,420 Episodes Processed | 582 Patterns Recorded | 18 Validated Concepts
- **Memory Promotion Notification Copy:**
  - *"System Event: Raw Pattern [XAUUSD-H1-Expansion-043] has completed walk-forward validation (Jaccard Similarity: 0.88) and has been promoted to Validated Concept memory."*
- **Judge Brain Audit Log Copy:**
  - *"Trade ID demo-trade-7901 audited. Classification: Earned Success. Support expansion structure successfully validated. Concept memory score updated (+2.4%)."*

---

## Pillar 3: Risk Intelligence (Exposure & Regimes)

Emotional trading leads to over-leverage and high correlation exposure. Risk Intelligence acts as an automated, passive guardrail, blocking dangerous signal fusions and warning users of portfolio-level hazards.

### Key Capabilities:
1. **Volatility Regime Mapping:** Detects sudden market volatility shifts and dynamically adjusts minimum signal confidence thresholds.
2. **Correlation Clustering Safeguard:** Prevents duplicate exposure by analyzing asset class correlations (e.g., restricting long positions on both XAUUSD and EURUSD if they share high directional correlation).
3. **Demo Account Risk Constraints:** Enforces a strict **10% daily risk limit** on virtual capital (exactly $119.40 USD out of the $1,194.00 USD initial balance).

### Interface & Copy Library:
- **Component Copy (Portfolio Risk Scorecard):**
  > **Active Risk Status:** `SECURE` (Active Margin Used: 0.00% | Correlation Risk Score: Low)
- **Risk Invalidation Notification Copy:**
  - *"Risk Guard Blocked: Signal on EURUSD rejected. Reason: Maximum correlation exposure limit for USD-dependent pairs exceeded."*
- **Demo Balance Warning Copy:**
  - *"Warning: Daily risk limits reached ($119.40 USD / 10%). Standard demo order execution is locked until the next daily interval resets. Learn to preserve capital."*

---

## Pillar 4: Explainable AI (Bilingual Reasoning & Context)

Black-box AI models generate anxiety and mistrust. Explainable AI (XAI) utilizes the Conversational Intelligence Layer to provide clear, detailed, and bilingual (Persian/English) justifications for every passive signal.

### Key Capabilities:
1. **Decision Explainer:** Translates complex mathematical price posture vectors into structured human answers.
2. **Bilingual AI Assistant Chatbot:** Responds to user queries regarding trade explanations, system limitations, and mistakes.

### Interface & Copy Library (Real-World XAI Examples):

#### Example 1: Active Trade Signal Reasoning (English)
```text
Symbol: XAUUSD
Direction: BUY
Timeframe Consensus: H4/H1 Bulllish
Confidence Score: 82%
Explainability Metrics:
- Structure: Base Expansion structure validated above the $2,310 support zone.
- Liquidity: Liquidity sweep of structural lows completed at $2,305.
- Risk Check: Approved (Correlation score: 0.12, Portfolio margin within bounds).
- Context Match: High Jaccard similarity (0.85) to historical concept [Bull-Expansion-H4-v3].
```

#### Example 2: Active Trade Signal Reasoning (Persian / فارسی)
```text
نماد: XAUUSD (طلا)
جهت پوزیشن: خرید (LONG)
تایم‌فریم‌های هم‌راستا: H4 و H1 صعودی
درصد اطمینان: ۸۲٪
معیارهای هوش تبیین‌پذیر:
- ساختار: تایید ساختار شکست و انبساط پایه (Base Expansion) بالای محدوده حمایتی ۲۳۱۰ دلار.
- نقدینگی: تکمیل پاکسازی نقدینگی (Liquidity Sweep) در کف ساختاری محدوده ۲۳۰۵ دلار.
- کنترل ریسک: تایید شده (ضریب همبستگی سبد دارایی: ۰.۱۲، میزان ریسک روزانه در محدوده مجاز).
- انطباق با حافظه: تطابق شباهت جاکارد بالا (۰.۸۵) با الگوی مفهومی تاریخی [Bull-Expansion-H4-v3].
```

#### Example 3: User Chatbot Inquiry & Response (Bilingual Q&A)
- **User Question (English):** *"Why is there no action signal for BTCUSD right now?"*
- **AI Response (English):** *"BTCUSD is currently in a high-volatility compression regime on the H1 timeframe. The Strategy Engine has flagged this segment as having an insufficient sample size for historical pattern matching (Jaccard similarity below 0.55). The Risk Engine has restricted action signals to prevent capital contamination during unstable volatility regimes."*
- **User Question (Persian):** *"چرا ربات تصمیم به فروش روی جفت ارز EURUSD نگرفت؟"*
- **AI Response (Persian):** *"پوزیشن فروش روی EURUSD به دلیل تداخل سیگنال در تایم‌فریم‌های کوتاه‌مدت صعودی (M15) و میان‌مدت نزولی (H4) رد شد. بر اساس مدل هم‌راستایی زمانی، سیگنال‌ها باید حداقل در ۵ تایم‌فریم هم‌راستا باشند. همچنین موتور ریسک به دلیل بالا بودن همبستگی با سبد دارایی فعلی، این تصمیم را مسدود کرده است."*
