import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Header } from './Header';
import { useTwinStore } from '../store/twinStore';
import { useAuthStore } from '../store/authStore';

beforeEach(() => {
  useTwinStore.setState(useTwinStore.getInitialState(), true);
  useAuthStore.setState({ token: null, email: null });
});

describe('Header', () => {
  it('shows zeroed stats and CONNECTING… when there is no snapshot yet', () => {
    render(<Header />);

    expect(screen.getByText('CONNECTING…')).toBeInTheDocument();
    expect(screen.getByRole('status', { name: 'System health: CONNECTING…' })).toBeInTheDocument();
  });

  it('derives active-failure and reconstructed counts from the snapshot', () => {
    useTwinStore.setState({
      systemHealth: 'degraded',
      snapshot: {
        masks: { '1': true, '2': false, '3': true },
        reconstructions: { '1': 42 },
        speeds: {},
        timestamp: 't',
      } as never,
      metrics: { rmse: 3.14159 } as never,
    });

    render(<Header />);

    expect(screen.getByText('2')).toBeInTheDocument(); // active failures
    expect(screen.getByText('1')).toBeInTheDocument(); // reconstructed
    expect(screen.getByText('3.14 mph')).toBeInTheDocument();
    expect(screen.getByText('DEGRADED')).toBeInTheDocument();
  });

  it('shows an em dash for RMSE when there are no metrics yet', () => {
    render(<Header />);
    expect(screen.getByText('—')).toBeInTheDocument();
  });

  it('opens the mission briefing when the MISSION button is clicked', async () => {
    useTwinStore.setState({ isBriefingOpen: false });
    const user = userEvent.setup();
    render(<Header />);

    await user.click(screen.getByRole('button', { name: 'MISSION' }));

    expect(useTwinStore.getState().isBriefingOpen).toBe(true);
  });

  it('renders the LoginGate sign-in control when logged out', () => {
    render(<Header />);
    expect(screen.getByLabelText('Sign in with Google')).toBeInTheDocument();
  });
});
