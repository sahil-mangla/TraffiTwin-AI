import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { useSystemState } from './useSystemState';
import { useTwinStore } from '../store/twinStore';
import { api } from '../api/trafitwin';
import type { SystemState } from '../types/api';

vi.mock('../api/trafitwin', () => ({
  api: {
    getState: vi.fn(),
  },
}));

function makeState(): SystemState {
  return {
    snapshot: { current_time: 0, readings: {}, masks: {}, reconstructions: {} },
    metrics: { fcr: 100, mae: 0, rmse: 0, total_failures_simulated: 0 },
    timestamp: new Date().toISOString(),
    system_health: 'healthy',
  };
}

beforeEach(() => {
  useTwinStore.setState(useTwinStore.getInitialState(), true);
  vi.clearAllMocks();
});

describe('useSystemState', () => {
  it('fetches state on mount and stores it via setSystemState', async () => {
    vi.mocked(api.getState).mockResolvedValue(makeState());

    const { unmount } = renderHook(() => useSystemState());

    await waitFor(() => expect(useTwinStore.getState().snapshot).not.toBeNull());
    expect(api.getState).toHaveBeenCalledTimes(1);
    expect(useTwinStore.getState().isBackendOffline).toBe(false);
    unmount();
  });

  it('marks the backend offline when the fetch fails', async () => {
    vi.mocked(api.getState).mockRejectedValue(new Error('network error'));

    const { unmount } = renderHook(() => useSystemState());

    await waitFor(() => expect(useTwinStore.getState().isBackendOffline).toBe(true));
    unmount();
  });

  it('returns a refetch function that re-invokes the API', async () => {
    vi.mocked(api.getState).mockResolvedValue(makeState());
    const { result, unmount } = renderHook(() => useSystemState());

    await waitFor(() => expect(api.getState).toHaveBeenCalledTimes(1));
    await result.current.refetch();

    expect(api.getState).toHaveBeenCalledTimes(2);
    unmount();
  });
});
