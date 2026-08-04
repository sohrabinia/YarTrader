export const CONFIG = {
  apiBaseUrl:
    import.meta.env.VITE_API_BASE_URL || "http://localhost:8000",

  wsBaseUrl:
    (import.meta.env.VITE_API_BASE_URL || "http://localhost:8000")
      .replace(/^http/, "ws"),
};
