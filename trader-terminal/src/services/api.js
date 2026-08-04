import { CONFIG } from "../core/config";

const buildUrl = (endpoint) => {
  if (endpoint.startsWith("http")) {
    return endpoint;
  }
  return `${CONFIG.apiBaseUrl}${endpoint}`;
};

const getAuthHeaders = () => {
  const token = localStorage.getItem('tradeyar_token');
  return token ? { 'Authorization': `Bearer ${token}` } : {};
};

// Implement Fetch helper with timeout
const fetchWithTimeout = async (url, options = {}, timeoutMs = 15000) => {
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal
    });
    clearTimeout(id);
    return response;
  } catch (error) {
    clearTimeout(id);
    if (error.name === 'AbortError') {
      throw new Error(`Request timed out after ${timeoutMs}ms.`);
    }
    throw error;
  }
};

export const apiService = {
  async get(endpoint, timeoutMs = 15000) {
    const url = buildUrl(endpoint);
    const headers = getAuthHeaders();
    try {
      const resp = await fetchWithTimeout(url, { method: 'GET', headers }, timeoutMs);

      if (!resp.ok) {
        let errText = `HTTP Error ${resp.status}`;
        try {
          const errData = await resp.json();
          if (errData && errData.detail) errText = errData.detail;
        } catch (_) {}
        throw new Error(errText);
      }

      // Safe JSON validation check to avoid parsing crashes
      const contentType = resp.headers.get("content-type") || "";
      if (!contentType.includes("application/json")) {
        throw new Error(`Invalid response format from server. Expected JSON, received '${contentType}'.`);
      }

      return await resp.json();
    } catch (err) {
      console.error(`[API GET ERROR] Failed on ${endpoint}:`, err);
      // Ensure clear error propagation
      throw new Error(err.message || "Failed to communicate with TradeYar Backend Services.");
    }
  },

  async post(endpoint, data, timeoutMs = 15000) {
    const url = buildUrl(endpoint);
    const headers = {
      'Content-Type': 'application/json',
      ...getAuthHeaders()
    };
    try {
      const resp = await fetchWithTimeout(url, {
        method: 'POST',
        headers,
        body: JSON.stringify(data)
      }, timeoutMs);

      if (!resp.ok) {
        let errText = `HTTP Error ${resp.status}`;
        try {
          const errData = await resp.json();
          if (errData && errData.detail) errText = errData.detail;
        } catch (_) {}
        throw new Error(errText);
      }

      const contentType = resp.headers.get("content-type") || "";
      if (!contentType.includes("application/json")) {
        throw new Error(`Invalid response format from server. Expected JSON, received '${contentType}'.`);
      }

      return await resp.json();
    } catch (err) {
      console.error(`[API POST ERROR] Failed on ${endpoint}:`, err);
      throw new Error(err.message || "Failed to communicate with TradeYar Backend Services.");
    }
  }
};
