const envApiBase = import.meta.env.VITE_API_BASE_URL;
const envWsBase = import.meta.env.VITE_WS_BASE_URL;

// In production build, default strictly to relative paths ("") to guarantee CORS-free,
// same-origin operations, bypassing any development local overrides.
const isProd = import.meta.env.PROD;

export const CONFIG = {
  apiBaseUrl: isProd ? "" : (envApiBase || ""),
  wsBaseUrl: envWsBase || (typeof window !== "undefined" ? `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}` : "")
};
