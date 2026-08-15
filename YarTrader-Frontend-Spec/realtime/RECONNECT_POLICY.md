# RECONNECT_POLICY.md — Reconnection and Backoff Policy

This document defines the strict, non-blocking reconnection algorithms required for the client-side WebSocket client.

---

## 📈 Exponential Backoff with Jitter

When a connection fails or is severed, do not overwhelm the server by retrying at fixed intervals. Implement **Exponential Backoff with Jitter** to distribute server load during network outages.

### Reconnect Formula:

$$\text{Delay} = \min(\text{Max Delay}, \text{Base Delay} \times 2^{\text{Attempt}}) + \text{Jitter}$$

Where:
- **`Base Delay`:** `1000ms` (1 second)
- **`Max Delay`:** `30000ms` (30 seconds)
- **`Max Attempts`:** `5` consecutive retries before transitioning to `FAILED` / manual reset state.
- **`Jitter`:** Random noise between `-250ms` and `+250ms` to prevent multiple clients from synchronizing retry requests.

---

## 💻 Sample Implementation (TypeScript)

```typescript
class WebSocketClient {
  private ws: WebSocket | null = null;
  private attempt = 0;
  private baseDelay = 1000;
  private maxDelay = 30000;
  private maxAttempts = 5;

  public connect(url: string) {
    this.ws = new WebSocket(url);

    this.ws.onopen = () => {
      console.log("WebSocket connected.");
      this.attempt = 0; // Reset attempts on successful connection
    };

    this.ws.onclose = () => {
      this.handleReconnect(url);
    };

    this.ws.onerror = (err) => {
      console.error("WebSocket error observed:", err);
    };
  }

  private handleReconnect(url: string) {
    if (this.attempt >= this.maxAttempts) {
      console.error("Max reconnection attempts reached. Manual action required.");
      this.updateUIState("FAILED");
      return;
    }

    this.attempt++;
    this.updateUIState("RECONNECTING", this.attempt);

    // Calculate Backoff delay with 2^attempt
    const backoff = Math.min(this.maxDelay, this.baseDelay * Math.pow(2, this.attempt));
    const jitter = (Math.random() - 0.5) * 500; // ±250ms jitter
    const delay = backoff + jitter;

    console.log(`Retrying connection in ${Math.round(delay)}ms (Attempt ${this.attempt})`);
    setTimeout(() => {
      this.connect(url);
    }, delay);
  }

  private updateUIState(state: string, attemptCount = 0) {
    // Reducer dispatch to trigger state-aware UI cards or toasts
  }
}
```

---

## 🔄 Offline Data Persistence & Mock Fallbacks

During an active reconnecting state:
1. **Freeze Chart Tick Updates:** Do not clear existing charts or market data. Freeze lines and overlay an italic message: *"Live price updates suspended. Reconnecting..."*.
2. **Offline Mode Fallbacks:** If the client is completely offline (e.g., `navigator.onLine === false`), bypass socket retries entirely. Trigger an instant banner: *"No internet connection detected."* and wait for the browser's `online` event before retrying.
