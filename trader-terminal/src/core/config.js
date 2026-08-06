// Core configuration & overrides
export const CONFIG = {
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL || window.location.origin,
  wsBaseUrl: (import.meta.env.VITE_API_BASE_URL || window.location.origin).replace(/^http/, 'ws'),
};
