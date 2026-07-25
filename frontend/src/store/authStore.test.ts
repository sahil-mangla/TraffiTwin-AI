import { describe, it, expect, beforeEach } from 'vitest';
import { useAuthStore } from './authStore';

describe('authStore', () => {
  beforeEach(() => {
    localStorage.clear();
    useAuthStore.setState({ token: null, email: null });
  });

  it('starts logged out with no token in localStorage', () => {
    expect(useAuthStore.getState().token).toBeNull();
  });

  it('login stores the token and email, and persists to localStorage', () => {
    useAuthStore.getState().login('abc123', 'user@example.com');

    expect(useAuthStore.getState().token).toBe('abc123');
    expect(useAuthStore.getState().email).toBe('user@example.com');
    expect(localStorage.getItem('traffitwin_auth_token')).toBe('abc123');
  });

  it('logout clears the token, email, and localStorage', () => {
    useAuthStore.getState().login('abc123', 'user@example.com');
    useAuthStore.getState().logout();

    expect(useAuthStore.getState().token).toBeNull();
    expect(useAuthStore.getState().email).toBeNull();
    expect(localStorage.getItem('traffitwin_auth_token')).toBeNull();
  });
});
