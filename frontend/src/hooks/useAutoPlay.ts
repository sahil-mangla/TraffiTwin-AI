import { useEffect, useRef } from 'react';
import { api } from '../api/trafitwin';
import { useTwinStore } from '../store/twinStore';

const STEP_DELAY_MS = 1200; // pause between autoplay steps

export function useAutoPlay(refetch: () => Promise<void>) {
  const isAutoplay = useTwinStore((s) => s.isAutoplay);
  const isBackendOffline = useTwinStore((s) => s.isBackendOffline);
  const inFlightRef = useRef(false);
  const activeRef = useRef(isAutoplay);
  activeRef.current = isAutoplay;

  useEffect(() => {
    if (!isAutoplay || isBackendOffline) return;

    let cancelled = false;

    async function loop() {
      while (activeRef.current && !cancelled) {
        if (inFlightRef.current) {
          await sleep(100);
          continue;
        }

        inFlightRef.current = true;
        try {
          await api.stepSimulation(1);
          await refetch();
        } catch {
          // backend error — back off
          await sleep(2000);
        } finally {
          inFlightRef.current = false;
        }

        await sleep(STEP_DELAY_MS);
      }
    }

    loop();

    return () => {
      cancelled = true;
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAutoplay, isBackendOffline]);
}

function sleep(ms: number) {
  return new Promise<void>((r) => setTimeout(r, ms));
}
