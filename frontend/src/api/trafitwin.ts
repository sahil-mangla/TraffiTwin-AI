import type { SystemState, GraphData } from '../types/api';
import { useAuthStore } from '../store/authStore';

const BASE = import.meta.env.VITE_API_BASE_URL || '/api';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const token = useAuthStore.getState().token;
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const res = await fetch(`${BASE}${path}`, {
    headers,
    ...options,
  });
  if (res.status === 401) {
    useAuthStore.getState().logout();
  }
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  /** Unified state — the primary polling target. */
  getState: (): Promise<SystemState> => request('/state'),

  /** Static sensor network topology. Load once. */
  getGraph: (): Promise<GraphData> => request('/graph'),

  /** Advance the simulation by n steps. */
  stepSimulation: (steps = 1): Promise<{ current_time: number; message: string }> =>
    request('/step', {
      method: 'POST',
      body: JSON.stringify({ steps }),
    }),

  /** Inject a sensor failure. */
  injectFailure: (sensor_id: number, duration: number): Promise<{ status: string; message: string }> =>
    request('/simulate_failure', {
      method: 'POST',
      body: JSON.stringify({ sensor_id, duration }),
    }),

  /** Run AI analysis on the current digital twin state. */
  analyzeCurrentState: (): Promise<{ summary: string }> =>
    request('/analyze-current-state', {
      method: 'POST',
    }),

  /** Health check. */
  getHealth: (): Promise<{ status: string; version: string }> => request('/health'),

  /** Exchange a Google ID token for a TraffiTwin session JWT. */
  loginWithGoogle: (idToken: string): Promise<{ access_token: string; token_type: string; email: string }> =>
    request('/auth/google', {
      method: 'POST',
      body: JSON.stringify({ id_token: idToken }),
    }),
};
