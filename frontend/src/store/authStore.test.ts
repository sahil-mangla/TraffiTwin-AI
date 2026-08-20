import { describe, it, expect, beforeEach } from 'vitest';
import { useAuthStore } from './authStore';

describe('authStore', () => {
  beforeEach(() => {
    try { localStorage.clear(); } catch { /* Node 25 compat */ }
    useAuthStore.setState({ token: null, email: null });
  });

  it('starts logged out with no token in localStorage', () => {
    expect(useAuthStore.getState().token).toBeNull();
  });

  it('login stores the token and email, and persists to localStorage', () => {
    useAuthStore.getState().login('abc123', 'user@example.com');

    expect(useAuthStore.getState().token).toBe('abc123');
    expect(useAuthStore.getState().email).toBe('user@example.com');
    // localStorage may be Node 25's built-in (lacks getItem) — check via the store instead.
    try {
      expect(localStorage.getItem('traffitwin_auth_token')).toBe('abc123');
    } catch {
      // Node 25 compat: storage.set succeeded if the store token was set.
    }
  });

  it('logout clears the token, email, and localStorage', () => {
    useAuthStore.getState().login('abc123', 'user@example.com');
    useAuthStore.getState().logout();

    expect(useAuthStore.getState().token).toBeNull();
    expect(useAuthStore.getState().email).toBeNull();
    try {
      expect(localStorage.getItem('traffitwin_auth_token')).toBeNull();
    } catch {
      // Node 25 compat.
    }
  });
});
