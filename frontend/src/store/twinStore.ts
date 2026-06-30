import { create } from 'zustand';
import type { TwinSnapshot, TwinMetrics, TwinEvent, SystemState } from '../types/api';
import { api } from '../api/trafitwin';

// ── Analysis Feed Types ─────────────────────────────────────────────────────
export type AnalysisSource =
  | 'analyze_system_state'
  | 'current_failures'
  | 'recent_incidents'
  | 'performance_metrics'
  | 'custom_query';

export interface AnalysisCard {
  id: string;
  timestamp: string;
  title: string;
  response: string;
  sources: AnalysisSource[];
}

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

  // ── Analysis Feed ──────────────────────────────────────────────────────────
  analysisFeed: AnalysisCard[];

  // ── Startup Briefing Modal ──────────────────────────────────────────────────
  isBriefingOpen: boolean;

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
  runQuickAction: (action: AnalysisSource, customQuery?: string) => Promise<void>;
  openBriefing: () => void;
  closeBriefing: () => void;
  clearAnalysisFeed: () => void;
}

let eventCounter = 0;
let cardCounter = 0;

function makeId() {
  return `evt-${Date.now()}-${++eventCounter}`;
}

function makeCardId() {
  return `card-${Date.now()}-${++cardCounter}`;
}

const QUICK_ACTION_TITLES: Record<AnalysisSource, string> = {
  analyze_system_state: 'System State Analysis',
  current_failures: 'Active Failure Report',
  recent_incidents: 'Incident Summary',
  performance_metrics: 'Performance Metrics Report',
  custom_query: 'Custom Analysis',
};

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
  analysisFeed: [],
  isBriefingOpen: true,

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
        newEvents.push({
          id: makeId(),
          timestamp: new Date().toISOString(),
          severity: 'FAULT',
          message: `Sensor ${id} went offline`,
          sensor_id: Number(id),
        });
        set({ activeBanner: { type: 'fault', message: 'SENSOR FAILURE DETECTED', subtitle: `Sensor ${id} offline` } });
      }

      if (!failed && wasFailed) {
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

    // Diff reconstructions — detect when AI actually starts reconstructing a failed sensor
    const prevRecons = prev?.reconstructions ?? {};
    for (const id of Object.keys(recons)) {
      const wasRecon = id in prevRecons;
      if (!wasRecon) {
        newEvents.push({
          id: makeId(),
          timestamp: new Date().toISOString(),
          severity: 'AI_RESPONSE',
          message: `AI reconstruction engaged for Sensor ${id}`,
          sensor_id: Number(id),
        });
        set({ activeBanner: { type: 'ai', message: 'AI RECONSTRUCTION ENGAGED', subtitle: 'Recovering observability' } });
      }
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
      console.error('AI Analysis failed:', e);
    } finally {
      set({ isAnalyzing: false });
    }
  },

  async runQuickAction(action: AnalysisSource, customQuery?: string) {
    set({ isAnalyzing: true });
    try {
      const res = await api.analyzeCurrentState();
      const card: AnalysisCard = {
        id: makeCardId(),
        timestamp: new Date().toISOString(),
        title: customQuery
          ? `Query: ${customQuery.length > 40 ? customQuery.slice(0, 40) + '…' : customQuery}`
          : QUICK_ACTION_TITLES[action],
        response: res.summary,
        sources: [action],
      };
      set((s) => ({
        analysisFeed: [card, ...s.analysisFeed].slice(0, 20),
        latestIncidentSummary: res.summary,
      }));
    } catch (e) {
      console.error('Quick action failed:', e);
      const errorCard: AnalysisCard = {
        id: makeCardId(),
        timestamp: new Date().toISOString(),
        title: QUICK_ACTION_TITLES[action],
        response: 'Analysis failed. Backend may be offline or unavailable.',
        sources: [action],
      };
      set((s) => ({
        analysisFeed: [errorCard, ...s.analysisFeed].slice(0, 20),
      }));
    } finally {
      set({ isAnalyzing: false });
    }
  },

  openBriefing() {
    set({ isBriefingOpen: true });
  },

  closeBriefing() {
    set({ isBriefingOpen: false });
  },

  clearAnalysisFeed() {
    set({ analysisFeed: [] });
  },
}));
