# SHADOWS.md — Shadows & Glowing Accents

In TradeYar AI's dark-themed interface, shadow layers do not represent traditional soft shadows on white paper. Instead, they represent depth levels using a blend of dark-scale gradients and glowing neon accents (representing real-time system state and process liveness).

---

## 🕶️ Depth Levels & Shadows

| Shadow Token | CSS Style Value | Applied Component | Depth Role |
| :--- | :--- | :--- | :--- |
| **Flat** | `box-shadow: none;` | Standard background grids, static tables | Baseline surface |
| **Shadow Small** | `0 1px 2px rgba(0, 0, 0, 0.5)` | Input fields, active buttons, checkboxes | Level 1: Focus |
| **Shadow Medium**| `0 4px 6px -1px rgba(0, 0, 0, 0.6), 0 2px 4px -1px rgba(0, 0, 0, 0.5)` | System cards, blog previews, menu items | Level 2: Platform cards |
| **Shadow Large** | `0 10px 15px -3px rgba(0, 0, 0, 0.7), 0 4px 6px -2px rgba(0, 0, 0, 0.6)` | Floating sidebar drawers, dropdown menus | Level 3: Overlay |
| **Shadow Modal** | `0 25px 50px -12px rgba(0, 0, 0, 0.9)` | Central modal panels, authentication overlays | Level 4: Priority Modals |

---

## ⚡ Neon Pulsating Indicators & Glows

To represent the active heartbeats of backend tasks (such as active MT5 connections and worker recovery states), the frontend implements active glowing shadows coupled with CSS keyframe animation pulses.

```css
/* Core Pulsating Glow Keyframes */
@keyframes pulse-neon-primary {
  0% {
    box-shadow: 0 0 8px rgba(0, 229, 255, 0.3), inset 0 0 4px rgba(0, 229, 255, 0.1);
  }
  50% {
    box-shadow: 0 0 16px rgba(0, 229, 255, 0.6), inset 0 0 8px rgba(0, 229, 255, 0.2);
  }
  100% {
    box-shadow: 0 0 8px rgba(0, 229, 255, 0.3), inset 0 0 4px rgba(0, 229, 255, 0.1);
  }
}

@keyframes pulse-neon-success {
  0% {
    box-shadow: 0 0 8px rgba(0, 230, 118, 0.3);
  }
  50% {
    box-shadow: 0 0 16px rgba(0, 230, 118, 0.6);
  }
  100% {
    box-shadow: 0 0 8px rgba(0, 230, 118, 0.3);
  }
}

@keyframes pulse-neon-critical {
  0% {
    box-shadow: 0 0 8px rgba(255, 23, 68, 0.3);
  }
  50% {
    box-shadow: 0 0 20px rgba(255, 23, 68, 0.8);
  }
  100% {
    box-shadow: 0 0 8px rgba(255, 23, 68, 0.3);
  }
}
```

### 🏷️ Shadow Applied Class Rules:

1. **Active SRE Service Indicator:** Apply `animation: pulse-neon-success 2s infinite;` to show background threads functioning normally.
2. **Platform Degraded Alert:** Apply static `--shadow-neon-primary` to represent warning notifications.
3. **Emergency SRE Shutdown Trigger:** Apply `animation: pulse-neon-critical 1.5s infinite;` on the Emergency stop panels and error state modals.
