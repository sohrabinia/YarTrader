# UX rules: permission-rules.md

This document regulates permission-based visual behaviors in the UI workspace.

---

## 1. Contextual Disabling vs. Hiding
- Controls requiring elevated privileges (e.g. Risk Limit Configuration in Admin Console) must be clearly labeled and disabled if the user's JWT scope is insufficient.
- Interactive trading execution features are strictly forbidden on signals with the `RESEARCH` state.

## 2. Permission Banner Overlays
- When a page requires higher tier access (e.g. Premium Terminal), display a blurred background behind a centered modal explaining access options (SaaS tiers: USER, PRO, PREMIUM, ADMIN).
- Provide clean, secure links to update subscription settings.
