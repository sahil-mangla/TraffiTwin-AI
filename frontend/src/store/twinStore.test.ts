import { describe, it, expect, vi, beforeEach } from 'vitest';
import { useTwinStore } from './twinStore';
import { api } from '../api/trafitwin';
import type { SystemState, TwinSnapshot } from '../types/api';

vi.mock('../api/trafitwin', () => ({
  api: {
    analyzeCurrentState: vi.fn(),
  },
}));

function makeSnapshot(overrides: Partial<TwinSnapshot> = {}): TwinSnapshot {
  return {
    current_time: 0,
    readings: {},
    masks: {},
    reconstructions: {},
    ...overrides,
  };
}

function makeState(overrides: Partial<SystemState> = {}): SystemState {
  return {
    snapshot: makeSnapshot(),
    metrics: { fcr: 100, mae: 0, rmse: 0, total_failures_simulated: 0 },
    timestamp: new Date().toISOString(),
    system_health: 'healthy',
    ...overrides,
  };
}

function resetStore() {
  useTwinStore.setState(useTwinStore.getInitialState(), true);
}

describe('twinStore', () => {
  beforeEach(() => {
    resetStore();
    vi.clearAllMocks();
  });

  it('setSystemState stores the snapshot, metrics, and health', () => {
    const state = makeState({ system_health: 'degraded' });
    useTwinStore.getState().setSystemState(state, null);

    const s = useTwinStore.getState();
    expect(s.snapshot).toBe(state.snapshot);
    expect(s.metrics).toBe(state.metrics);
    expect(s.systemHealth).toBe('degraded');
    expect(s.isBackendOffline).toBe(false);
    expect(s.isLoading).toBe(false);
  });

  it('emits a FAULT event and fault banner when a sensor newly fails', () => {
    const first = makeState({ snapshot: makeSnapshot({ masks: { '5': false } }) });
    useTwinStore.getState().setSystemState(first, null);

    const second = makeState({ snapshot: makeSnapshot({ masks: { '5': true } }) });
    useTwinStore.getState().setSystemState(second, null);

    const s = useTwinStore.getState();
    expect(s.events[0].severity).toBe('FAULT');
    expect(s.events[0].sensor_id).toBe(5);
    expect(s.activeBanner?.type).toBe('fault');
  });

  it('emits a RECOVERY event distinguishing AI-reconstructed recovery from plain recovery', () => {
    const failing = makeState({ snapshot: makeSnapshot({ masks: { '5': true }, reconstructions: { '5': 42 } }) });
    useTwinStore.getState().setSystemState(failing, null);

    const recovered = makeState({ snapshot: makeSnapshot({ masks: { '5': false } }) });
    useTwinStore.getState().setSystemState(recovered, null);

    const s = useTwinStore.getState();
    expect(s.events[0].severity).toBe('RECOVERY');
    expect(s.events[0].message).toContain('AI reconstruction');
    expect(s.activeBanner?.type).toBe('recovery');
  });

  it('emits an AI_RESPONSE event when reconstruction newly engages for a sensor', () => {
    const first = makeState({ snapshot: makeSnapshot({ masks: { '5': true } }) });
    useTwinStore.getState().setSystemState(first, null);

    const second = makeState({ snapshot: makeSnapshot({ masks: { '5': true }, reconstructions: { '5': 30 } }) });
    useTwinStore.getState().setSystemState(second, null);

    const s = useTwinStore.getState();
    expect(s.events.some((e) => e.severity === 'AI_RESPONSE' && e.sensor_id === 5)).toBe(true);
  });

  it('caps the events list at 50 entries', () => {
    useTwinStore.getState().setSystemState(makeState(), null);
    for (let i = 0; i < 60; i++) {
      useTwinStore.getState().addEvent({ severity: 'SYSTEM', message: `event ${i}` });
    }
    expect(useTwinStore.getState().events.length).toBe(50);
  });

  it('clearEvents empties the events list', () => {
    useTwinStore.getState().addEvent({ severity: 'SYSTEM', message: 'hello' });
    useTwinStore.getState().clearEvents();
    expect(useTwinStore.getState().events).toEqual([]);
  });

  it('toggleAutoplay flips isAutoplay', () => {
    expect(useTwinStore.getState().isAutoplay).toBe(false);
    useTwinStore.getState().toggleAutoplay();
    expect(useTwinStore.getState().isAutoplay).toBe(true);
    useTwinStore.getState().toggleAutoplay();
    expect(useTwinStore.getState().isAutoplay).toBe(false);
  });

  it('setBackendStatus and setLoading update their respective flags', () => {
    useTwinStore.getState().setBackendStatus(true);
    expect(useTwinStore.getState().isBackendOffline).toBe(true);

    useTwinStore.getState().setLoading(false);
    expect(useTwinStore.getState().isLoading).toBe(false);
  });

  it('setSelectedSensor stores and clears the selected sensor id', () => {
    useTwinStore.getState().setSelectedSensor(7);
    expect(useTwinStore.getState().selectedSensorId).toBe(7);
    useTwinStore.getState().setSelectedSensor(null);
    expect(useTwinStore.getState().selectedSensorId).toBeNull();
  });

  it('dismissBanner clears the active banner', () => {
    useTwinStore.setState({ activeBanner: { type: 'fault', message: 'x' } });
    useTwinStore.getState().dismissBanner();
    expect(useTwinStore.getState().activeBanner).toBeNull();
  });

  it('runAnalysis stores the summary and resets isAnalyzing on success', async () => {
    vi.mocked(api.analyzeCurrentState).mockResolvedValue({ summary: 'all good' });

    const promise = useTwinStore.getState().runAnalysis();
    expect(useTwinStore.getState().isAnalyzing).toBe(true);
    await promise;

    expect(useTwinStore.getState().isAnalyzing).toBe(false);
    expect(useTwinStore.getState().latestIncidentSummary).toBe('all good');
  });

  it('runAnalysis resets isAnalyzing even when the API call fails', async () => {
    vi.mocked(api.analyzeCurrentState).mockRejectedValue(new Error('boom'));

    await useTwinStore.getState().runAnalysis();

    expect(useTwinStore.getState().isAnalyzing).toBe(false);
  });

  it('runQuickAction appends a success card to the analysis feed', async () => {
    vi.mocked(api.analyzeCurrentState).mockResolvedValue({ summary: 'summary text' });

    await useTwinStore.getState().runQuickAction('current_failures');

    const feed = useTwinStore.getState().analysisFeed;
    expect(feed).toHaveLength(1);
    expect(feed[0].title).toBe('Active Failure Report');
    expect(feed[0].response).toBe('summary text');
  });

  it('runQuickAction truncates long custom queries in the card title', async () => {
    vi.mocked(api.analyzeCurrentState).mockResolvedValue({ summary: 'ok' });
    const longQuery = 'a'.repeat(60);

    await useTwinStore.getState().runQuickAction('custom_query', longQuery);

    const feed = useTwinStore.getState().analysisFeed;
    expect(feed[0].title.startsWith('Query: ')).toBe(true);
    expect(feed[0].title.length).toBeLessThan(longQuery.length);
  });

  it('runQuickAction appends an error card when the API call fails', async () => {
    vi.mocked(api.analyzeCurrentState).mockRejectedValue(new Error('offline'));

    await useTwinStore.getState().runQuickAction('recent_incidents');

    const feed = useTwinStore.getState().analysisFeed;
    expect(feed[0].response).toContain('Analysis failed');
  });

  it('caps the analysis feed at 20 entries', async () => {
    vi.mocked(api.analyzeCurrentState).mockResolvedValue({ summary: 'ok' });
    for (let i = 0; i < 25; i++) {
      await useTwinStore.getState().runQuickAction('performance_metrics');
    }
    expect(useTwinStore.getState().analysisFeed.length).toBe(20);
  });

  it('clearAnalysisFeed empties the feed', async () => {
    vi.mocked(api.analyzeCurrentState).mockResolvedValue({ summary: 'ok' });
    await useTwinStore.getState().runQuickAction('performance_metrics');
    useTwinStore.getState().clearAnalysisFeed();
    expect(useTwinStore.getState().analysisFeed).toEqual([]);
  });

  it('openBriefing and closeBriefing toggle isBriefingOpen', () => {
    useTwinStore.getState().closeBriefing();
    expect(useTwinStore.getState().isBriefingOpen).toBe(false);
    useTwinStore.getState().openBriefing();
    expect(useTwinStore.getState().isBriefingOpen).toBe(true);
  });
});
