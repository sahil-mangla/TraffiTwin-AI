import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import App from './App';
import { useTwinStore } from './store/twinStore';
import { api } from './api/trafitwin';

vi.mock('./api/trafitwin', () => ({
  api: {
    getHealth: vi.fn(),
    getState: vi.fn(),
    getGraph: vi.fn(),
    stepSimulation: vi.fn(),
    injectFailure: vi.fn(),
  },
}));

const LAYOUT_JSON = [{ id: 0, x: 0.5, y: 0.5 }];

beforeEach(() => {
  // Start in ready state so the wake-up overlay doesn't block the test UI.
  useTwinStore.setState({ ...useTwinStore.getInitialState(), wakeUpStatus: 'ready' }, true);
  vi.clearAllMocks();
  vi.mocked(api.getHealth).mockResolvedValue({ status: 'ok', version: '1.0.0' });
  vi.mocked(api.getState).mockResolvedValue({
    snapshot: { current_time: 0, readings: {}, masks: {}, reconstructions: {} },
    metrics: { fcr: 100, mae: 0, rmse: 0, total_failures_simulated: 0 },
    timestamp: new Date().toISOString(),
    system_health: 'healthy',
  });
});

describe('App', () => {
  it('mounts the main operations layout once the graph layout loads', async () => {
    vi.mocked(api.getGraph).mockResolvedValue({ nodes: [], edges: [] });
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ json: () => Promise.resolve(LAYOUT_JSON) })
    );

    render(<App />);

    expect(screen.getByRole('heading', { name: 'TraffiTwin AI' })).toBeInTheDocument();
    await waitFor(() => expect(screen.getByRole('img')).toBeInTheDocument());
    expect(screen.getByLabelText('Operations Intelligence Rail')).toBeInTheDocument();
    expect(screen.queryByText(/Network topology unavailable/)).not.toBeInTheDocument();

    vi.unstubAllGlobals();
  });

  it('falls back to a circular layout and shows a warning when the graph fetch fails', async () => {
    vi.mocked(api.getGraph).mockRejectedValue(new Error('network error'));
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('network error')));

    render(<App />);

    await waitFor(() =>
      expect(screen.getByText(/Network topology unavailable/)).toBeInTheDocument()
    );
    expect(screen.getByRole('img')).toBeInTheDocument();

    vi.unstubAllGlobals();
  });
});
