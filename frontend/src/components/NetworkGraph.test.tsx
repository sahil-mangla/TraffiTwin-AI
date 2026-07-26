import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { NetworkGraph } from './NetworkGraph';
import { useTwinStore } from '../store/twinStore';
import type { GraphLayoutNode } from '../types/api';

const LAYOUT: GraphLayoutNode[] = [{ id: 0, x: 0.5, y: 0.5 }];

let resizeCallback: ResizeObserverCallback | null = null;

class MockResizeObserver {
  constructor(cb: ResizeObserverCallback) {
    resizeCallback = cb;
  }
  observe() {}
  disconnect() {}
  unobserve() {}
}

beforeEach(() => {
  useTwinStore.setState(useTwinStore.getInitialState(), true);
  resizeCallback = null;
  vi.stubGlobal('ResizeObserver', MockResizeObserver);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

function triggerResize(width: number, height: number) {
  resizeCallback?.(
    [{ contentRect: { width, height } } as unknown as ResizeObserverEntry],
    {} as ResizeObserver
  );
}

describe('NetworkGraph', () => {
  it('renders a canvas with an accessible summary of the network', () => {
    render(<NetworkGraph layout={LAYOUT} edges={[]} />);

    const canvas = screen.getByRole('img');
    expect(canvas.tagName).toBe('CANVAS');
    expect(canvas).toHaveAccessibleName(/207 sensors operational/);
  });

  it('reflects failed and reconstructed sensor counts in the legend', () => {
    useTwinStore.setState({
      snapshot: {
        current_time: 1,
        readings: {},
        masks: { '0': true, '1': true },
        reconstructions: { '0': 50 },
      },
    });
    render(<NetworkGraph layout={LAYOUT} edges={[]} />);

    expect(screen.getByText('Failed (2)')).toBeInTheDocument();
    expect(screen.getByText('Reconstructed (1)')).toBeInTheDocument();
  });

  it('selects the node under the click after layout coordinates are computed', () => {
    const setSelectedSensor = vi.fn();
    useTwinStore.setState({ setSelectedSensor });
    render(<NetworkGraph layout={LAYOUT} edges={[]} />);

    const canvas = screen.getByRole('img');
    canvas.getBoundingClientRect = () =>
      ({ left: 0, top: 0, width: 100, height: 100 } as DOMRect);
    triggerResize(100, 100);

    fireEvent.click(canvas, { clientX: 50, clientY: 50 });

    expect(setSelectedSensor).toHaveBeenCalledWith(0);
  });

  it('deselects when clicking away from any node', () => {
    const setSelectedSensor = vi.fn();
    useTwinStore.setState({ setSelectedSensor });
    render(<NetworkGraph layout={LAYOUT} edges={[]} />);

    const canvas = screen.getByRole('img');
    canvas.getBoundingClientRect = () =>
      ({ left: 0, top: 0, width: 100, height: 100 } as DOMRect);
    triggerResize(100, 100);

    fireEvent.click(canvas, { clientX: 5, clientY: 5 });

    expect(setSelectedSensor).toHaveBeenCalledWith(null);
  });

  it('shows a tooltip on hover near a node', () => {
    render(<NetworkGraph layout={LAYOUT} edges={[]} />);

    const canvas = screen.getByRole('img');
    canvas.getBoundingClientRect = () =>
      ({ left: 0, top: 0, width: 100, height: 100 } as DOMRect);
    triggerResize(100, 100);

    fireEvent.mouseMove(canvas, { clientX: 50, clientY: 50 });

    expect(screen.getByText('SENSOR 0')).toBeInTheDocument();
  });
});
