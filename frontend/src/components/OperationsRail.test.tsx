import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { OperationsRail } from './OperationsRail';
import { useTwinStore } from '../store/twinStore';
import { useAuthStore } from '../store/authStore';
import type { TwinSnapshot, TwinMetrics } from '../types/api';

const SNAPSHOT: TwinSnapshot = {
  current_time: 1,
  readings: Object.fromEntries(Array.from({ length: 10 }, (_, i) => [String(i), 60])),
  masks: { '0': true, '1': true },
  reconstructions: { '0': 55 },
};

const METRICS: TwinMetrics = { fcr: 0.9, mae: 1.5, rmse: 2.1, total_failures_simulated: 4 };

beforeEach(() => {
  useTwinStore.setState(useTwinStore.getInitialState(), true);
  useTwinStore.setState({ isLoading: false, snapshot: SNAPSHOT, metrics: METRICS });
});

describe('OperationsRail', () => {
  it('shows loading placeholders until a snapshot and metrics are available', () => {
    useTwinStore.setState({ isLoading: true });
    const { container } = render(<OperationsRail />);
    expect(screen.queryByLabelText('Operations Intelligence Rail')).not.toBeInTheDocument();
    expect(container.querySelectorAll('.animate-pulse').length).toBeGreaterThan(0);
  });

  it('renders network observability and derived metrics once loaded', () => {
    render(<OperationsRail />);

    expect(screen.getByLabelText('Operations Intelligence Rail')).toBeInTheDocument();
    expect(screen.getByText('1.50')).toBeInTheDocument(); // MAE
    expect(screen.getByText('4')).toBeInTheDocument(); // SIM OPS
  });

  it('shows the empty analysis feed state with no cards', () => {
    render(<OperationsRail />);
    expect(screen.getByText(/No analyses yet/)).toBeInTheDocument();
  });

  it('renders an analysis card with its data-source label', () => {
    useTwinStore.setState({
      analysisFeed: [
        {
          id: 'card-1',
          timestamp: new Date().toISOString(),
          title: 'System State Analysis',
          response: 'All systems nominal.',
          sources: ['analyze_system_state'],
        },
      ],
    });
    render(<OperationsRail />);

    expect(screen.getByText('System State Analysis')).toBeInTheDocument();
    expect(screen.getByText('All systems nominal.')).toBeInTheDocument();
    expect(screen.getByText('SYS-STATE')).toBeInTheDocument();
  });

  it('shows the analyzing indicator while a quick action is in flight', () => {
    useTwinStore.setState({ isAnalyzing: true });
    render(<OperationsRail />);
    expect(screen.getByText('ANALYZING…')).toBeInTheDocument();
  });

  it('runs a quick action when authenticated', async () => {
    useAuthStore.setState({ token: 'test-token', email: 'test@example.com' });
    const runQuickAction = vi.fn();
    useTwinStore.setState({ runQuickAction });
    const user = userEvent.setup();
    render(<OperationsRail />);

    await user.click(screen.getByRole('button', { name: /Failures/ }));

    expect(runQuickAction).toHaveBeenCalledWith('current_failures');
  });

  it('disables quick actions and suggestions when logged out', () => {
    useAuthStore.setState({ token: null, email: null });
    render(<OperationsRail />);

    expect(screen.getByRole('button', { name: /System State/ })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Which sensors are offline?' })).toBeDisabled();
  });

  it('submits a custom query and clears the input', async () => {
    const runQuickAction = vi.fn();
    useTwinStore.setState({ runQuickAction });
    const user = userEvent.setup();
    render(<OperationsRail />);

    const input = screen.getByPlaceholderText('Ask the analyst…');
    await user.type(input, 'What is the FCR?');
    await user.click(screen.getByRole('button', { name: '↑' }));

    expect(runQuickAction).toHaveBeenCalledWith('custom_query', 'What is the FCR?');
    expect(input).toHaveValue('');
  });

  it('clears the analysis feed when Clear is clicked', async () => {
    const clearAnalysisFeed = vi.fn();
    useTwinStore.setState({
      clearAnalysisFeed,
      analysisFeed: [
        { id: 'card-1', timestamp: new Date().toISOString(), title: 'x', response: 'y', sources: ['current_failures'] },
      ],
    });
    const user = userEvent.setup();
    render(<OperationsRail />);

    await user.click(screen.getByRole('button', { name: 'Clear' }));

    expect(clearAnalysisFeed).toHaveBeenCalled();
  });
});
