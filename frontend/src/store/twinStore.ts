import { create } from 'zustand';
import type { TwinSnapshot, TwinMetrics, TwinEvent, SystemState } from '../types/api';
import { api } from '../api/trafitwin';

interface TwinStore {
  // ── Data ──────────────────────────────────────────────────────────────────
  snapshot: TwinSnapshot | null;
  metrics: TwinMetrics | null;
  events: TwinEvent[];
  systemHealth: 'healthy' | 'degraded' | 'critical' | 'unknown';

  // ── UI state ──────────────────────────────────────────────────────────────
  isAutoplay: boolean;
  isLoading: boolean;
  isBackendOffline: boolean;
  lastUpdated: Date | null;
  selectedSensorId: number | null;

  // ── Storytelling banner ───────────────────────────────────────────────────
  activeBanner: { type: 'fault' | 'ai' | 'recovery'; message: string; subtitle?: string } | null;

  // ── AI Operations Analyst ──────────────────────────────────────────────────
  latestIncidentSummary: string | null;
  isAnalyzing: boolean;

  // ── Actions ───────────────────────────────────────────────────────────────
  setSystemState: (state: SystemState, prevSnapshot: TwinSnapshot | null) => void;
  addEvent: (event: Omit<TwinEvent, 'id' | 'timestamp'>) => void;
  clearEvents: () => void;
  setBackendStatus: (offline: boolean) => void;
  toggleAutoplay: () => void;
  setLoading: (v: boolean) => void;
  setSelectedSensor: (id: number | null) => void;
  dismissBanner: () => void;
  runAnalysis: () => Promise<void>;
}

let eventCounter = 0;

function makeId() {
  return `evt-${Date.now()}-${++eventCounter}`;
}

export const useTwinStore = create<TwinStore>((set, get) => ({
  snapshot: null,
  metrics: null,
  events: [],
  systemHealth: 'unknown',
  isAutoplay: false,
  isLoading: true,
  isBackendOffline: false,
  lastUpdated: null,
  selectedSensorId: null,
  activeBanner: null,
  latestIncidentSummary: null,
  isAnalyzing: false,

  setSystemState(state, prevSnapshot) {
    const { snapshot: prev } = get();
    const prevMasks = prev?.masks ?? prevSnapshot?.masks ?? {};
    const newMasks = state.snapshot.masks;
    const recons = state.snapshot.reconstructions;
    const newEvents: TwinEvent[] = [];

    // Diff masks — detect new faults and recoveries
    for (const [id, failed] of Object.entries(newMasks)) {
      const wasFailed = prevMasks[id] === true;

      if (failed && !wasFailed) {
        // New fault
        newEvents.push({
          id: makeId(),
          timestamp: new Date().toISOString(),
          severity: 'FAULT',
          message: `Sensor ${id} went offline`,
          sensor_id: Number(id),
        });
        newEvents.push({
          id: makeId(),
          timestamp: new Date().toISOString(),
          severity: 'AI_RESPONSE',
          message: `AI reconstruction engaged for Sensor ${id}`,
          sensor_id: Number(id),
        });
        // Trigger fault banner
        set({ activeBanner: { type: 'fault', message: 'SENSOR FAILURE DETECTED', subtitle: `Sensor ${id} offline` } });
        setTimeout(() => {
          const banner = get().activeBanner;
          if (banner?.type === 'fault') {
            set({ activeBanner: { type: 'ai', message: 'AI RECONSTRUCTION ENGAGED', subtitle: 'Recovering observability' } });
          }
        }, 2000);
      }

      if (!failed && wasFailed) {
        // Recovery
        const wasReconstructed = id in (prev?.reconstructions ?? {});
        newEvents.push({
          id: makeId(),
          timestamp: new Date().toISOString(),
          severity: 'RECOVERY',
          message: wasReconstructed
            ? `Sensor ${id} restored via AI reconstruction`
            : `Sensor ${id} returned to service`,
          sensor_id: Number(id),
        });
        set({ activeBanner: { type: 'recovery', message: 'TRAFFIC INTELLIGENCE RESTORED', subtitle: 'Network fully observable' } });
        setTimeout(() => {
          const banner = get().activeBanner;
          if (banner?.type === 'recovery') set({ activeBanner: null });
        }, 4000);
      }
    }

    // If active reconstructions exist mid-step, show ongoing AI banner
    const reconIds = Object.keys(recons);
    if (reconIds.length > 0 && newEvents.length === 0) {
      // Steady-state reconstruction — no new events, just keep working silently
    }

    set((s) => ({
      snapshot: state.snapshot,
      metrics: state.metrics,
      systemHealth: state.system_health,
      lastUpdated: new Date(),
      isBackendOffline: false,
      isLoading: false,
      latestIncidentSummary: state.latest_incident_summary || null,
      events: newEvents.length
        ? [...newEvents, ...s.events].slice(0, 50)
        : s.events,
    }));
  },

  addEvent(event) {
    const full: TwinEvent = {
      id: makeId(),
      timestamp: new Date().toISOString(),
      ...event,
    };
    set((s) => ({ events: [full, ...s.events].slice(0, 50) }));
  },

  clearEvents() {
    set({ events: [] });
  },

  setBackendStatus(offline) {
    set({ isBackendOffline: offline });
  },

  toggleAutoplay() {
    set((s) => ({ isAutoplay: !s.isAutoplay }));
  },

  setLoading(v) {
    set({ isLoading: v });
  },

  setSelectedSensor(id) {
    set({ selectedSensorId: id });
  },

  dismissBanner() {
    set({ activeBanner: null });
  },

  async runAnalysis() {
    set({ isAnalyzing: true });
    try {
      const res = await api.analyzeCurrentState();
      set({ latestIncidentSummary: res.summary });
    } catch (e) {
      console.error("AI Analysis failed:", e);
    } finally {
      set({ isAnalyzing: false });
    }
  },
}));
