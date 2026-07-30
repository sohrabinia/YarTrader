# ADMIN GUIDE
**TradeYar AI Platform Administration Manual**

This manual outlines system management instructions for platform owners and administrators.

---

## 1. Accessing the Admin Intelligence Center
The administrator center `/admin` is strictly isolated and guarded by the role verification dependency `require_role(["ADMIN"])`.

To log in:
1. Navigate to `/login`.
2. Enter the default pre-seeded credentials:
   - **Email**: `admin@tradeyar.ai`
   - **Password**: `AdminPassSecure!123`
3. Upon success, an active session token is registered, and the **Admin Center** option appears in your navigation header.

---

## 2. Managing Users & Subscriptions
The admin console loads a complete list of registered users dynamically:
- **Inspect Role**: See who is on USER (FREE), PRO, or PREMIUM.
- **Update Role**: Select the PRO or PREMIUM action buttons. This fires our monetization layer, registering a completed crypto transaction, generating email billing receipts, and sending Telegram notifications.

---

## 3. Product Analytics & Cost Logs
Keep track of platform operations:
- **Total Registrations**: Counter tracking sign-up conversions.
- **Total Page Views**: Real-time traffic log.
- **Total Support Queries**: Tracks overall AI Assistant usage.
- **AI Request Limits**: System administrators can monitor the daily request count per user. If a user abuses resources, cost limits automatically throttle API requests, keeping infrastructure costs to absolute zero.

---

## 4. Content AI Approval Pipeline
TradeYar integrates an autonomous multi-agent content writer.
- Admins can trigger the AI generation pipeline by passing a target financial topic (e.g., "Consolidation bounds").
- The Content AI System fires agents sequentially: `ResearchAgent` -> `WriterAgent` -> `TranslatorAgent` (FA) -> `SEOAgent` -> `Quality Fact Check` -> `Risk Safety Check`.
- Draft content appears in the publishing queue. Click **Approve & Publish** to finalize the article on the blog and automatically broadcast it to our Telegram educational channels!
