// Core configuration & overrides
let apiBase = import.meta.env.VITE_API_BASE_URL || window.location.origin;
if (apiBase && apiBase.endsWith('/')) {
  apiBase = apiBase.slice(0, -1);
}

export const CONFIG = {
  apiBaseUrl: apiBase,
  wsBaseUrl: apiBase.replace(/^http/, 'ws'),
};
