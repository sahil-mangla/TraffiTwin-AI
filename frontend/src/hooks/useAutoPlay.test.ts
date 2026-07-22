import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook } from '@testing-library/react';
import { useAutoPlay } from './useAutoPlay';
import { useTwinStore } from '../store/twinStore';
import { api } from '../api/trafitwin';

vi.mock('../api/trafitwin', () => ({
  api: {
    stepSimulation: vi.fn(),
  },
}));

beforeEach(() => {
  useTwinStore.setState(useTwinStore.getInitialState(), true);
  vi.clearAllMocks();
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
});

describe('useAutoPlay', () => {
  it('does nothing while autoplay is off', async () => {
    const refetch = vi.fn().mockResolvedValue(undefined);
    renderHook(() => useAutoPlay(refetch));

    await vi.advanceTimersByTimeAsync(5000);

    expect(api.stepSimulation).not.toHaveBeenCalled();
    expect(refetch).not.toHaveBeenCalled();
  });

  it('steps the simulation and refetches on a timer once autoplay is on', async () => {
    vi.mocked(api.stepSimulation).mockResolvedValue({ current_time: 1, message: 'ok' });
    const refetch = vi.fn().mockResolvedValue(undefined);

    useTwinStore.setState({ isAutoplay: true });
    const { unmount } = renderHook(() => useAutoPlay(refetch));

    await vi.advanceTimersByTimeAsync(1200);

    expect(api.stepSimulation).toHaveBeenCalledWith(1);
    expect(refetch).toHaveBeenCalled();
    unmount();
  });

  it('does not step while the backend is marked offline', async () => {
    const refetch = vi.fn().mockResolvedValue(undefined);
    useTwinStore.setState({ isAutoplay: true, isBackendOffline: true });
    renderHook(() => useAutoPlay(refetch));

    await vi.advanceTimersByTimeAsync(5000);

    expect(api.stepSimulation).not.toHaveBeenCalled();
  });

  it('stops looping once the effect is cleaned up', async () => {
    vi.mocked(api.stepSimulation).mockResolvedValue({ current_time: 1, message: 'ok' });
    const refetch = vi.fn().mockResolvedValue(undefined);

    useTwinStore.setState({ isAutoplay: true });
    const { unmount } = renderHook(() => useAutoPlay(refetch));

    await vi.advanceTimersByTimeAsync(1200);
    unmount();
    vi.mocked(api.stepSimulation).mockClear();

    await vi.advanceTimersByTimeAsync(5000);
    expect(api.stepSimulation).not.toHaveBeenCalled();
  });
});
