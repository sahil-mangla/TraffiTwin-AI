import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { IncidentDrawer } from './IncidentDrawer';
import { useTwinStore } from '../store/twinStore';
import type { GraphLayoutNode, TwinSnapshot } from '../types/api';

const layout: GraphLayoutNode[] = [
  { id: 1, x: 0.1, y: 0.1 },
  { id: 2, x: 0.11, y: 0.11 }, // close neighbor of node 1
  { id: 3, x: 0.9, y: 0.9 },
];

function makeSnapshot(overrides: Partial<TwinSnapshot> = {}): TwinSnapshot {
  return {
    current_time: 0,
    readings: {},
    masks: {},
    reconstructions: {},
    ...overrides,
  };
}

beforeEach(() => {
  useTwinStore.setState(useTwinStore.getInitialState(), true);
});

describe('IncidentDrawer', () => {
  it('renders nothing when no sensor is selected', () => {
    const { container } = render(<IncidentDrawer layout={layout} />);
    expect(container).toBeEmptyDOMElement();
  });

  it('shows HEALTHY status for a sensor with no active failure', () => {
    useTwinStore.setState({ selectedSensorId: 1, snapshot: makeSnapshot({ masks: { '1': false } }) });
    render(<IncidentDrawer layout={layout} />);

    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(screen.getAllByText('HEALTHY').length).toBeGreaterThan(0);
  });

  it('shows FAILED status for a sensor that is down without reconstruction', () => {
    useTwinStore.setState({ selectedSensorId: 1, snapshot: makeSnapshot({ masks: { '1': true } }) });
    render(<IncidentDrawer layout={layout} />);

    expect(screen.getAllByText('FAILED').length).toBeGreaterThan(0);
  });

  it('shows RECONSTRUCTED status and the AI estimate for a reconstructed sensor', () => {
    useTwinStore.setState({
      selectedSensorId: 1,
      snapshot: makeSnapshot({ masks: { '1': true }, readings: { '1': 40 }, reconstructions: { '1': 38.5 } }),
    });
    render(<IncidentDrawer layout={layout} />);

    expect(screen.getAllByText('RECONSTRUCTED').length).toBeGreaterThan(0);
    expect(screen.getByText('38.5 mph')).toBeInTheDocument();
    expect(screen.getByText('1.5 mph')).toBeInTheDocument(); // estimation error
  });

  it('counts nearby sensors within the proximity threshold', () => {
    useTwinStore.setState({ selectedSensorId: 1, snapshot: makeSnapshot() });
    render(<IncidentDrawer layout={layout} />);

    // Node 2 is close (within 0.15), node 3 is far — expect a count of 1.
    expect(screen.getByText('Nearby Sensors')).toBeInTheDocument();
    const row = screen.getByText('Nearby Sensors').closest('div');
    expect(row).toHaveTextContent('1');
  });

  it('closing the drawer clears the selected sensor', async () => {
    useTwinStore.setState({ selectedSensorId: 1, snapshot: makeSnapshot() });
    const user = userEvent.setup();
    render(<IncidentDrawer layout={layout} />);

    await user.click(screen.getByRole('button', { name: 'Close incident drawer' }));

    expect(useTwinStore.getState().selectedSensorId).toBeNull();
  });
});
