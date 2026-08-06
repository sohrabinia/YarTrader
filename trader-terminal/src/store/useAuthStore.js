// Auth store state and actions
export const useAuthStore = {
  getToken: () => localStorage.getItem('yartrader_token'),
  getRole: () => localStorage.getItem('yartrader_role'),
  getName: () => localStorage.getItem('yartrader_name'),
  setSession: (token, role, name) => {
    localStorage.setItem('yartrader_token', token);
    localStorage.setItem('yartrader_role', role);
    localStorage.setItem('yartrader_name', name);
  },
  clearSession: () => {
    localStorage.removeItem('yartrader_token');
    localStorage.removeItem('yartrader_role');
    localStorage.removeItem('yartrader_name');
  }
};
