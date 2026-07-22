import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { EventLogDrawer } from './EventTimeline';
import { useTwinStore } from '../store/twinStore';
import type { TwinEvent } from '../types/api';

function makeEvent(overrides: Partial<TwinEvent> = {}): TwinEvent {
  return {
    id: 'evt-1',
    timestamp: new Date().toISOString(),
    severity: 'SYSTEM',
    message: 'test event',
    ...overrides,
  };
}

beforeEach(() => {
  useTwinStore.setState(useTwinStore.getInitialState(), true);
});

describe('EventLogDrawer', () => {
  it('shows "No events recorded" when the drawer is opened with an empty log', async () => {
    const user = userEvent.setup();
    render(<EventLogDrawer />);

    await user.click(screen.getByRole('button', { name: /Event Log/i }));

    expect(screen.getByText('No events recorded.')).toBeInTheDocument();
  });

  it('renders event rows with severity label and message once opened', async () => {
    useTwinStore.setState({ events: [makeEvent({ severity: 'FAULT', message: 'Sensor 5 went offline' })] });
    const user = userEvent.setup();
    render(<EventLogDrawer />);

    await user.click(screen.getByRole('button', { name: /Event Log/i }));

    expect(screen.getByText('Sensor 5 went offline')).toBeInTheDocument();
    expect(screen.getByText('FAULT')).toBeInTheDocument();
  });

  it('shows the total event count badge on the toggle bar', () => {
    useTwinStore.setState({ events: [makeEvent(), makeEvent({ id: 'evt-2' })] });
    render(<EventLogDrawer />);

    expect(screen.getByText('2')).toBeInTheDocument();
  });

  it('clicking CLEAR empties the event log', async () => {
    useTwinStore.setState({ events: [makeEvent()] });
    const user = userEvent.setup();
    render(<EventLogDrawer />);

    await user.click(screen.getByRole('button', { name: /Event Log/i }));
    await user.click(screen.getByRole('button', { name: 'Clear event log' }));

    expect(useTwinStore.getState().events).toEqual([]);
  });

  it('toggling the drawer flips aria-expanded', async () => {
    const user = userEvent.setup();
    render(<EventLogDrawer />);

    const toggle = screen.getByRole('button', { name: /Event Log/i });
    expect(toggle).toHaveAttribute('aria-expanded', 'false');

    await user.click(toggle);
    expect(toggle).toHaveAttribute('aria-expanded', 'true');
  });
});
