# ALERT_DESIGN.md — Alert & Incident Design

This document outlines the visual layout guidelines and actions for active SRE incident cards and system error notifications.

---

## 🚨 SRE Incident Card Layout Specification

When a critical platform failure is observed (such as a database parse crash or service loss), the top of the SRE Admin Timeline must render a priority Incident Card.

```
┌──────────────────────────────────────────────────────────────┐
│ 🔴 CRITICAL INCIDENT: MT5 CONNECTION LOSS                    │
├──────────────────────────────────────────────────────────────┤
│ Code: MT5_ERR_503 | Subsystem: MT5_DATA_PROVIDER             │
│ Triggered: 2023-11-20 14:15:10 UTC | Retries Executed: 3/5    │
│                                                              │
│ Description:                                                 │
│ Core MT5 provider was disconnected by remote broker. Rates   │
│ pipeline is currently falling back to synthetic generator.   │
│                                                              │
│ [📋 Copy Error Logs]           [⚡ Force Restart MT5 Adapter]│
└──────────────────────────────────────────────────────────────┘
```

### Visual Styling Specs:
- **Card Border:** 2px solid neon red border (`--color-critical`), with `animation: pulse-neon-critical 1.5s infinite;` to ensure instant operator attention.
- **Card Background:** Intense dark gray `#162032` (Card BG) layered over base layout.
- **Action Buttons:**
  - **Copy Logs Button:** Secondary dark grey action.
  - **Force Restart Button:** Solid neon-red highlight action button. Displays a loading ring on click and executes a POST command to `/api/control`.

---

## 🔔 Client Alert System Notification Banners

For non-SRE standard users, critical backend failures must be presented gracefully without exposing internal paths or code stacktraces.

### User Terminal Notification Banner (`/dashboard/*`)
- **Visuals:** Safe amber horizontal bar appearing at the very top of the Trader Terminal.
- **English Banner Copy:**
  - *"System Notice: High network volatility is currently affecting live price feeds. Active virtual positions remain fully protected by our redundant safety engines."*
- **Persian Banner Copy:**
  - *"اطلاعیه سیستم: نوسانات شبکه در حال حاضر بر قیمت‌های زنده تأثیر گذاشته است. پوزیشن‌های مجازی فعال کاملاً توسط موتورهای پشتیبان محافظت می‌شوند."*
- **Interaction:** Floating banner must push downstream content layouts down rather than overlapping navigation or menus.
