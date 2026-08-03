// Core configuration & overrides
export const CONFIG = {
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL || (
    (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
      ? 'http://127.0.0.1:8000'
      : window.location.origin
  ),
  wsBaseUrl: (import.meta.env.VITE_API_BASE_URL || (
    (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
      ? 'http://127.0.0.1:8000'
      : window.location.origin
  )).replace(/^http/, 'ws'),
};
