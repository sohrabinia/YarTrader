// Standalone API Service for TradeYar AI Client

const getAuthHeaders = () => {
  const token = localStorage.getItem('tradeyar_token');
  return token ? { 'Authorization': `Bearer ${token}` } : {};
};

export const apiService = {
  async get(endpoint) {
    const headers = getAuthHeaders();
    const resp = await fetch(endpoint, { method: 'GET', headers });
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
    const resp = await fetch(endpoint, {
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
