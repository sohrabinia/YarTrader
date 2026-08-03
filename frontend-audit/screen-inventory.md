# screen-inventory.md

## Screen Inventory & User Experience Flow

Documents the three strictly isolated Single Page Application (SPA) screens served from the FastAPI backend:

### 1. Public Marketing Website
- **Sitemap Routes**: `/`, `/features`, `/pricing`, `/blog`
- **Branding**: Bloomberg/TradingView style dark theme with neon-green signals.
- **Allowed Actions**: Public pricing viewing, long-form blog reading, newsletter signup, and Apple/Google branded social logins.

### 2. Customer Trader Terminal
- **Sitemap Route**: `/dashboard/*`
- **Panels**:
  - **Shadow Trading Tracker**: Displays virtual positions, trigger levels, and real-time PnL.
  - **AI Research Observatory**: Interactive research assistants, multi-timeframe structural charts, and signal indicators.
- **Security Check**: Restricts access strictly to authenticated `PRO` & `PREMIUM` tokens.

### 3. SRE Admin Control Console
- **Sitemap Route**: `/admin/*`
- **Panels**:
  - **System Limits Panel**: Dynamic control of active symbols count, pipeline delay limits.
  - **Trace Monitor**: Real-time trace logs and SRE emergency stop triggers.
- **Security Check**: Enforces role-based JWT scope of `ADMIN` or `SRE`.
