# TradeYar AI — Lifecycle Notifications & Quota Alerts
*Document Reference: TY-REV-NOT-04*
*Category: User Notification Systems & Copy Assets*

---

## 1. Usage Warning Thresholds (Quota System)

TradeYar AI monitors three primary technical usage quotas to maintain system resources and enforce plan boundaries:
- **AI Analysis Queries:** Conversations with our bilingual assistant chatbot.
- **Backtest Simulations:** Chronological strategy evaluations run against historical tick data.
- **Active Monitored Symbols:** The concurrent symbols registered in the `SymbolRegistry` matrix.

To ensure transparency and prevent abrupt workspace interruptions, the system triggers real-time, non-intrusive notifications at specific capacity milestones.

---

### A. 70% Quota Capacity (Informational State)
- **Trigger:** Any of the user's active limits cross the 70% capacity threshold.
- **UI Delivery Channel:** A subtle, slide-in toast notification in the bottom-right corner of the terminal, plus a muted notification indicator in the user dashboard header.
- **Visual Design:** Slate gray background (`#1A1D20`), border with standard slate gray accent, white text, and a non-flashing status icon.
- **English Text:**
  > **Workspace Usage Notice**
  >
  > *You have consumed 70% of your monthly intelligence quota. Currently: 35 / 50 backtests completed. No action is required. Your workspace remains fully active.*
- **Persian (فارسی) Text:**
  > **اطلاعیه میزان مصرف فضای کار**
  >
  > *شما ۷۰٪ از سهمیه محاسباتی ماهانه خود را مصرف کرده‌اید. در حال حاضر: ۳۵ از ۵۰ شبیه‌سازی انجام شده است. نیازی به اقدامی نیست و فضای کار شما کاملاً فعال است.*

---

### B. 90% Quota Capacity (Warning State)
- **Trigger:** Usage metrics cross the 90% capacity threshold.
- **UI Delivery Channel:** A golden caution banner pinned to the top of the specific utility panel (e.g., above the Backtest Configuration panel or the Chatbot window), plus an in-app inbox message.
- **Visual Design:** Dark charcoal background (`#0D0F12`), glowing golden-yellow border (`#F1C40F`), black text on the badge, and a warning exclamation icon.
- **English Text:**
  > **Attention: Workspace Nearing Capacity Limits**
  >
  > *Your intelligence quota is close to its ceiling (45 / 50 backtests consumed). Upgrading your tier will unlock deeper multi-timeframe horizons, expanded active symbols, and unrestricted backtesting capabilities.*
  >
  > `[ View Upgrade Path ]`  `[ Dismiss Banner ]`
- **Persian (فارسی) Text:**
  > **هشدار: فضای کار در حال نزدیک شدن به سقف مجاز**
  >
  > *سهمیه محاسباتی شما به سقف مجاز نزدیک شده است (۴۵ از ۵۰ شبیه‌سازی مصرف شده). ارتقای سطح اشتراک، دسترسی به تایم‌فریم‌های کلان، نمادهای فعال بیشتر و شبیه‌سازی‌های نامحدود را فعال می‌کند.*
  >
  > `[ مشاهده مسیر ارتقا ]`  `[ بستن پیام ]`

---

### C. 100% Quota Capacity (Limit-Reached State)
- **Trigger:** Quota is completely exhausted (e.g., 50 / 50 backtests completed).
- **UI Delivery Channel:** Renders a clean glassmorphism `FeatureLock` overlay card directly on top of the affected module (such as the backtest form or the chat input window), disabling form inputs and button clicks. Standard market observation charts remain fully active.
- **Visual Design:** Transparent frosted-glass overlay (`rgba(13, 15, 18, 0.85)`), blur filter (8px), a sleek glowing padlock icon in the center, and a prominent call-to-action button.
- **English Text:**
  > **Intelligence Quota Exhausted**
  >
  > *You have reached 100% of your allocated Professional tier backtests (50 / 50 completed). To prevent resource thrashing, additional simulations are locked for the remainder of this billing cycle.*
  >
  > *Upgrade to our Advanced Trader tier today to unlock unlimited backtesting, portfolio-wide correlation safeguards, and high-fidelity simulated Shadow Trading.*
  >
  > `[ Upgrade Instantly to Advanced Trader ]`  `[ Return to Dashboard ]`
- **Persian (فارسی) Text:**
  > **سهمیه محاسباتی به پایان رسید**
  >
  > *شما به ۱۰۰٪ سهمیه شبیه‌سازی‌های تخصصی خود رسیده‌اید (۵۰ از ۵۰ شبیه‌سازی انجام شده). برای بهینه‌سازی منابع، بخش شبیه‌سازی تا پایان دوره جاری قفل شده است.*
  >
  > *امروز اشتراک خود را به سطح «معامله‌گر پیشرفته» ارتقا دهید تا شبیه‌سازی نامحدود، حفاظت همبستگی سبد دارایی و معاملات شبیه‌سازی شده سایه فعال شوند.*
  >
  > `[ ارتقای آنی به سطح معامله‌گر پیشرفته ]`  `[ بازگشت به داشبورد ]`

---

## 2. Pre-Expiration & Renewal Notifications

To maintain payment transparency and ensure uninterrupted analytical operations, the billing engine triggers countdown notifications before the automated renewal attempts.

---

### A. 14 Days Before Renewal
- **Trigger:** Subscription end-date is exactly 14 days away.
- **UI Delivery Channel:** In-app inbox alert, and a clean badge display inside the User Profile settings center.
- **English Copy:**
  > **Subscription Renewal Notice**
  >
  > *Your Professional Tier subscription will automatically renew in 14 days on 12 March 2027. Your linked payment method will be billed $19.00 USD. If you need to modify your billing configuration, please review your plan settings.*
- **Persian Copy:**
  > **اطلاعیه تمدید اشتراک**
  >
  > *اشتراک سطح تخصصی شما ۱۴ روز دیگر در تاریخ ۱۲ مارس ۲۰۲۷ به طور خودکار تمدید می‌شود. روش پرداخت شما با مبلغ ۱۹ دلار شارژ خواهد شد. در صورت نیاز به تغییر روش پرداخت یا لغو، تنظیمات اشتراک خود را بررسی کنید.*

---

### B. 7 Days Before Renewal
- **Trigger:** Subscription end-date is exactly 7 days away.
- **UI Delivery Channel:** A gentle banner displayed at the bottom of the dashboard layout.
- **English Copy:**
  > **Subscription Renewal is Approaching**
  >
  > *Your renewal date is 7 days away. Review your current workspace usage or modify your plan before the automatic transaction processes.*
  >
  > `[ Review Active Plan ]`
- **Persian Copy:**
  > **زمان تمدید اشتراک نزدیک است**
  >
  > *۷ روز تا تمدید اشتراک شما باقی مانده است. میزان مصرف فعلی خود را بررسی کرده یا در صورت نیاز، پیش از پردازش خودکار تراکنش نسبت به تغییر طرح اقدام کنید.*
  >
  > `[ بررسی اشتراک فعلی ]`

---

### C. 1 Day Before Renewal
- **Trigger:** Subscription end-date is exactly 24 hours away.
- **UI Delivery Channel:** Slide-in alert upon terminal login, plus a persistent golden dot in the profile settings menu.
- **English Copy:**
  > **Subscription Renews Tomorrow**
  >
  > *Your TradeYar AI subscription automatically renews tomorrow. Please ensure your payment method is active to prevent any interruption to your Advanced Reasoning and Shadow Trading workspace.*
  >
  > `[ Manage Billing Details ]`
- **Persian Copy:**
  > **تمدید اشتراک فردا انجام می‌شود**
  >
  > *اشتراک TradeYar AI شما فردا به طور خودکار تمدید خواهد شد. لطفاً مطمئن شوید روش پرداخت شما فعال است تا از وقفه در تحلیل‌های پیشرفته و معاملات سایه جلوگیری شود.*
  >
  > `[ مدیریت جزئیات پرداخت ]`
