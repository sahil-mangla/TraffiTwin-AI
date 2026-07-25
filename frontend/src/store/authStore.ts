import { create } from 'zustand';

const STORAGE_KEY = 'traffitwin_auth_token';

interface AuthStore {
  token: string | null;
  email: string | null;
  login: (token: string, email: string) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthStore>((set) => ({
  token: localStorage.getItem(STORAGE_KEY),
  email: null,

  login(token, email) {
    localStorage.setItem(STORAGE_KEY, token);
    set({ token, email });
  },

  logout() {
    localStorage.removeItem(STORAGE_KEY);
    set({ token: null, email: null });
  },
}));
