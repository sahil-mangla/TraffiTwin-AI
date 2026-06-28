import type { SystemState, GraphData } from '../types/api';

const BASE = '/api';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
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

  /** Health check. */
  getHealth: (): Promise<{ status: string; version: string }> => request('/health'),
};
