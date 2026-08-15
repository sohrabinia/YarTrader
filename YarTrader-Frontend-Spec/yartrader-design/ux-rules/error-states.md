# UX rules: error-states.md

This document standardizes error-handling layouts for the frontend client.

---

## 1. Graceful Degraded Layouts
- If a specific panel (e.g. AI Support API) fails to load, isolate the failure:
  - Keep the remainder of the workspace fully active.
  - Render a small alert block inside the degraded card with the message: `"Subsystem Temporarily Offline"`.

## 2. Interactive Retry Action
- Render an explicit `"Retry Connection"` action on the card if the error is recoverable (such as timeout or network drop).
- Log the correlation ID to the local system log console to enable immediate SRE tracing.
