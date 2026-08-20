import { create } from 'zustand';

const STORAGE_KEY = 'traffitwin_auth_token';

interface AuthStore {
  token: string | null;
  email: string | null;
  login: (token: string, email: string) => void;
  logout: () => void;
}

// Safe localStorage wrapper — guards against Node 25's built-in `localStorage`
// object (activated via --localstorage-file in Vitest 4 workers) which is
// incompatible with the Web Storage API and lacks getItem/setItem/removeItem.
const storage = {
  get(key: string): string | null {
    try { return localStorage.getItem(key); } catch { return null; }
  },
  set(key: string, value: string): void {
    try { localStorage.setItem(key, value); } catch { /* no-op in non-browser */ }
  },
  remove(key: string): void {
    try { localStorage.removeItem(key); } catch { /* no-op in non-browser */ }
  },
};

export const useAuthStore = create<AuthStore>((set) => ({
  token: storage.get(STORAGE_KEY),
  email: null,

  login(token, email) {
    storage.set(STORAGE_KEY, token);
    set({ token, email });
  },

  logout() {
    storage.remove(STORAGE_KEY);
    set({ token: null, email: null });
  },
}));
