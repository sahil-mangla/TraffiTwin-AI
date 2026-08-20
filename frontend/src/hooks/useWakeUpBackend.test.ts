import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook } from '@testing-library/react';
import { useWakeUpBackend } from './useWakeUpBackend';
import { useTwinStore } from '../store/twinStore';
import { api } from '../api/trafitwin';

vi.mock('../api/trafitwin', () => ({
  api: {
    getHealth: vi.fn(),
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

// ── Helpers ──────────────────────────────────────────────────────────────────

function getStatus() {
  return useTwinStore.getState().wakeUpStatus;
}

function getRetries() {
  return useTwinStore.getState().wakeUpRetries;
}

function isOffline() {
  return useTwinStore.getState().isBackendOffline;
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('useWakeUpBackend', () => {
  it('sets status=ready and clears offline flag when health succeeds immediately', async () => {
    vi.mocked(api.getHealth).mockResolvedValue({ status: 'ok', version: '1.0.0' });

    const { unmount } = renderHook(() => useWakeUpBackend());

    // Let the first ping resolve.
    await vi.runAllTimersAsync();

    expect(getStatus()).toBe('ready');
    expect(isOffline()).toBe(false);
    expect(api.getHealth).toHaveBeenCalledTimes(1);
    unmount();
  });

  it('stays in waking state and sets offline=true while health is failing', async () => {
    vi.mocked(api.getHealth).mockRejectedValue(new Error('503'));

    renderHook(() => useWakeUpBackend());

    // Run the first attempt.
    await vi.advanceTimersByTimeAsync(0);

    expect(getStatus()).toBe('waking');
    expect(isOffline()).toBe(true);
  });

  it('retries on failure and transitions to ready once health succeeds', async () => {
    vi.mocked(api.getHealth)
      .mockRejectedValueOnce(new Error('503'))
      .mockRejectedValueOnce(new Error('503'))
      .mockResolvedValue({ status: 'ok', version: '1.0.0' });

    const { unmount } = renderHook(() => useWakeUpBackend());

    // Advance through two failures + their backoff delays + the successful third.
    await vi.runAllTimersAsync();

    expect(getStatus()).toBe('ready');
    expect(isOffline()).toBe(false);
    expect(api.getHealth).toHaveBeenCalledTimes(3);
    unmount();
  });

  it('increments wakeUpRetries on each failed attempt', async () => {
    vi.mocked(api.getHealth)
      .mockRejectedValueOnce(new Error('503'))
      .mockRejectedValueOnce(new Error('503'))
      .mockResolvedValue({ status: 'ok', version: '1.0.0' });

    const { unmount } = renderHook(() => useWakeUpBackend());

    await vi.runAllTimersAsync();

    // retries === 2 (the count updated by the two failed attempts; 0-indexed)
    expect(getRetries()).toBeGreaterThanOrEqual(2);
    unmount();
  });

  it('sets status=failed and keeps offline=true after MAX_RETRIES exhausted', async () => {
    vi.mocked(api.getHealth).mockRejectedValue(new Error('503'));

    const { unmount } = renderHook(() => useWakeUpBackend());

    // Run all timers so every retry + its delay fires.
    await vi.runAllTimersAsync();

    expect(getStatus()).toBe('failed');
    expect(isOffline()).toBe(true);
    unmount();
  });

  it('stops retrying once the hook is unmounted', async () => {
    let resolveHealth!: () => void;
    vi.mocked(api.getHealth).mockImplementation(
      () => new Promise<{ status: string; version: string }>((_, reject) => {
        resolveHealth = () => reject(new Error('503'));
      })
    );

    const { unmount } = renderHook(() => useWakeUpBackend());

    unmount(); // cancel before any retry can complete
    resolveHealth?.();

    await vi.runAllTimersAsync();

    // Status should still be 'waking' (the initial store default), not 'failed'.
    expect(getStatus()).toBe('waking');
  });
});
