// Auth store state and actions
export const useAuthStore = {
  getToken: () => localStorage.getItem('tradeyar_token'),
  getRole: () => localStorage.getItem('tradeyar_role'),
  getName: () => localStorage.getItem('tradeyar_name'),
  setSession: (token, role, name) => {
    localStorage.setItem('tradeyar_token', token);
    localStorage.setItem('tradeyar_role', role);
    localStorage.setItem('tradeyar_name', name);
  },
  clearSession: () => {
    localStorage.removeItem('tradeyar_token');
    localStorage.removeItem('tradeyar_role');
    localStorage.removeItem('tradeyar_name');
  }
};
