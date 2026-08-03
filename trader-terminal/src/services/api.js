// Standalone API Service for TradeYar AI Client
import { CONFIG } from '../core/config.js';

const getFullUrl = (endpoint) => {
  if (endpoint.startsWith('/')) {
    return `${CONFIG.apiBaseUrl}${endpoint}`;
  }
  return endpoint;
};

const getAuthHeaders = () => {
  const token = localStorage.getItem('tradeyar_token');
  return token ? { 'Authorization': `Bearer ${token}` } : {};
};

export const apiService = {
  async get(endpoint) {
    const headers = getAuthHeaders();
    const url = getFullUrl(endpoint);
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
    const url = getFullUrl(endpoint);
    const resp = await fetch(url, {
      method: 'POST',
      headers,
      body: JSON.stringify(data)
    });
    if (!resp.ok) {
      const errData = await resp.json().catch(() => ({}));
      throw new Error(errData.detail || `API Error: ${resp.status}`);
    }
    return resp.json();
  }
};
