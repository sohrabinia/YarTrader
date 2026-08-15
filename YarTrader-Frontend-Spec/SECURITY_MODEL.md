# SECURITY_MODEL.md - Frontend Security & Audit Model

This document specifies the security boundaries, role mappings, and audit exposure rules for the TradeYar AI frontend.

---

## 1. Zero Trust Frontend Model

The frontend is strictly a **renderer** and a **control surface**. It possesses zero authorization authority.
- All controls, visibility rules, and actions are determined exclusively by the backend via JWT scopes.
- Hidden UI elements do not equal security. Any action must validate backend permissions.
- Hardcoding credentials, API secrets, or administrative tokens in the client is strictly forbidden.

---

## 2. Role-Based Capabilities

The UI must restrict interactive panels according to user scopes:
- **USER:** View public marketing page, view basic features, view read-only user metrics.
- **PRO & PREMIUM:** Access the Customer Financial Intelligence Terminal, view shadow trading telemetry, interact with AI Research Support.
- **ADMIN / SRE:** Access the Admin Control Console and SRE Console, adjust system limit parameters, toggle system emergency states.

---

## 3. Audit Visibility Rules

Sensitive operations performed in the UI must explicitly expose auditing details:
- **Eligible Actions:**
  - Risk Overrides
  - Execution Permissions/Toggles
  - System Limit Changes
  - User Scope Modifications

- **Mandatory Audit Payload Fields (Exposed on screen):**
  - **Actor:** User ID / Username who performed the action.
  - **Timestamp:** Exact date and time (ISO UTC) of the action.
  - **Approving Engine:** System engine verifying the change.
  - **Current State:** Before and after value state.
  - **Correlation ID:** Unique ID tracing the backend execution path.
