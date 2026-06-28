import { useEffect, useRef } from 'react';
import { api } from '../api/trafitwin';
import { useTwinStore } from '../store/twinStore';

const POLL_IDLE_MS = 5000; // when autoplay is off

export function useSystemState() {
  const setSystemState = useTwinStore((s) => s.setSystemState);
  const setBackendStatus = useTwinStore((s) => s.setBackendStatus);
  const addEvent = useTwinStore((s) => s.addEvent);
  const snapshot = useTwinStore((s) => s.snapshot);
  const snapshotRef = useRef(snapshot);
  snapshotRef.current = snapshot;

  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  async function fetchState() {
    try {
      const state = await api.getState();
      setSystemState(state, snapshotRef.current);
    } catch {
      setBackendStatus(true);
    }
  }

  // Initial load + idle polling
  useEffect(() => {
    fetchState();

    function schedule() {
      timerRef.current = setTimeout(async () => {
        await fetchState();
        schedule();
      }, POLL_IDLE_MS);
    }

    schedule();

    addEvent({ severity: 'SYSTEM', message: 'TraffiTwin AI connected. Network monitoring active.' });

    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return { refetch: fetchState };
}
