// Standalone API Service for YarTrader Client
import { CONFIG } from '../core/config.js';

const getAuthHeaders = () => {
  const token = localStorage.getItem('yartrader_token');
  return token ? { 'Authorization': `Bearer ${token}` } : {};
};

export const apiService = {
  async get(endpoint) {
    const headers = getAuthHeaders();
    const url = endpoint.startsWith('http') ? endpoint : `${CONFIG.apiBaseUrl}${endpoint}`;
    const resp = await fetch(url, { method: 'GET', headers });
    if (!resp.ok) {
      throw new Error(`API Error: ${resp.status} - ${resp.statusText}`);
    }
    return resp.json();
  },

  async post(endpoint, data) {
    const headers = {
      'Content-Type': 'application/json',
      ...getAuthHeaders()
    };
    const url = endpoint.startsWith('http') ? endpoint : `${CONFIG.apiBaseUrl}${endpoint}`;
    const resp = await fetch(url, {
      method: 'POST',
      headers,
      body: JSON.stringify(data)
    });
    if (!resp.ok) {
      const errData = await resp.json().catch(() => ({}));
      let message = `API Error: ${resp.status}`;
      if (typeof errData.detail === "string") {
        message = errData.detail;
      } else if (Array.isArray(errData.detail)) {
        message = errData.detail
          .map(e => e.msg || JSON.stringify(e))
          .join("; ");
      }
      throw new Error(message);
    }
    return resp.json();
  }
};
