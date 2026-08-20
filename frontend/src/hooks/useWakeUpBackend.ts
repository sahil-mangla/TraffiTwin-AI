import { useEffect, useRef } from 'react';
import { api } from '../api/trafitwin';
import { useTwinStore } from '../store/twinStore';

// ── Retry configuration ────────────────────────────────────────────────────
// HF free-tier Spaces typically take 30–90 s to cold-start.
// Exponential backoff: 2 s → 4 s → 8 s → 16 s → 30 s (capped), 10 attempts.
// Total max wait ≈ 2 + 4 + 8 + 16 + 30 × 6 = 210 s ≈ 3.5 min.
const MAX_RETRIES = 10;
const BASE_DELAY_MS = 2_000;
const MAX_DELAY_MS = 30_000;

function backoffDelay(attempt: number): number {
  return Math.min(BASE_DELAY_MS * 2 ** attempt, MAX_DELAY_MS);
}

/**
 * On mount, probes the backend `/health` endpoint and retries with
 * exponential backoff until it responds.  Writes `wakeUpStatus` into
 * `twinStore` so components can show differentiated UX:
 *
 *   'waking'  – health check in flight / retrying (HF Space cold-start)
 *   'ready'   – backend responded; normal polling can begin
 *   'failed'  – all retries exhausted; show hard-failure message
 */
export function useWakeUpBackend() {
  const setWakeUpStatus = useTwinStore((s) => s.setWakeUpStatus);
  const setBackendStatus = useTwinStore((s) => s.setBackendStatus);
  const cancelledRef = useRef(false);

  useEffect(() => {
    cancelledRef.current = false;

    async function probe() {
      for (let attempt = 0; attempt < MAX_RETRIES; attempt++) {
        if (cancelledRef.current) return;

        try {
          await api.getHealth();
          if (cancelledRef.current) return;
          // Backend responded — mark ready and clear offline flag.
          setWakeUpStatus('ready', attempt);
          setBackendStatus(false);
          return;
        } catch {
          if (cancelledRef.current) return;
          // Still waking — update retry counter so the overlay can display it.
          setWakeUpStatus('waking', attempt + 1);
          setBackendStatus(true);
        }

        // Wait before the next attempt.
        await sleep(backoffDelay(attempt));
      }

      // All retries exhausted.
      if (!cancelledRef.current) {
        setWakeUpStatus('failed', MAX_RETRIES);
        setBackendStatus(true);
      }
    }

    probe();

    return () => {
      cancelledRef.current = true;
    };
  // Run once on mount only.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
}

function sleep(ms: number) {
  return new Promise<void>((r) => setTimeout(r, ms));
}
