# YarTrader — Vercel Live Deployment Configuration & Notes

This guide provides simple, non-technical instructions on how to connect the YarTrader frontend single-page application on Vercel to a real running backend instance, ensuring that actual live data is displayed instead of local demo fallback data.

---

## 1. CURRENT BACKEND STATUS
* **Backend Location:** Currently configured to run locally (`127.0.0.1:8000`).
* **Publicly Reachable:** **NO** (Local-only, running on the SRE windows development host).
* **Important Note:** Vercel servers run on the cloud and **cannot** reach a backend that is bound only to `localhost` or `127.0.0.1` on your local computer. To display real-time live data on the production URL (`https://yartrader.vercel.app`), the backend must be made publicly reachable.

---

## 2. HOW TO CONNECT VERCEL TO THE REAL BACKEND
We have eliminated the hardcoded dependency on `https://tradeyar.ai`. All API calls are now routed dynamically through a secure, server-side Vercel Proxy function.

To connect Vercel to your backend:
1. Open your **Vercel Project Dashboard** at `https://vercel.com/`.
2. Go to **Settings** -> **Environment Variables**.
3. Add a new Environment Variable with:
   * **Key:** `BACKEND_API_URL`
   * **Value:** `<The public URL of your running backend>` (for example: `https://api.yartrader.app` or your public IP address).
4. Save the variable and **Redeploy** the project.

No code modifications are required when the backend URL changes in the future! Simply update the value of `BACKEND_API_URL` in Vercel settings.

---

## 3. HOW TO EXPOSE A LOCAL WINDOWS BACKEND PUBLICLY (TEMPORARY SOLUTIONS)
If your backend is running on a local Windows machine and you want Vercel to be able to connect to it temporarily for testing before deploying to a production VPS, you can use one of these secure tunnel utilities:

### Option A: Cloudflare Tunnel (Recommended)
1. Download the Cloudflare Tunnel daemon (`cloudflared`) on your Windows machine.
2. Run the tunnel command:
   ```cmd
   cloudflared tunnel --url http://localhost:8000
   ```
3. Cloudflare will generate a secure, public HTTPS URL (for example: `https://your-unique-subdomain.trycloudflare.com`).
4. Set this generated HTTPS URL as the `BACKEND_API_URL` in your Vercel Project Dashboard.

### Option B: ngrok
1. Download and install ngrok on your local computer.
2. Expose port 8000 by running:
   ```cmd
   ngrok http 8000
   ```
3. ngrok will provide a public forwarding URL (for example: `https://abcd-123-45.ngrok-free.app`).
4. Set this URL as the `BACKEND_API_URL` in your Vercel Project Dashboard.

---

## 4. DESIGN BEHAVIOR & FAIL-CLOSED PROTECTION
* **LIVE Mode:** Indicated by a **green** `LIVE` badge in the header. Only active if the frontend successfully connects and validates a response from the real backend.
* **DEMO Mode:** Indicated by a **yellow** `DEMO / MOCK` badge. Active during local offline testing.
* **BACKEND UNREACHABLE Mode:** Indicated by a **red** `BACKEND UNREACHABLE` badge and a prominent full-screen warning banner, explicitly alerting the user that the connection is offline and the displayed data is Demo data. This guarantees that mock data never silently masquerades as live data.
