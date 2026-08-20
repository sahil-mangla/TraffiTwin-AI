import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { BackendOfflineOverlay } from './BackendOfflineOverlay';
import { useTwinStore } from '../store/twinStore';

beforeEach(() => {
  useTwinStore.setState(useTwinStore.getInitialState(), true);
});

describe('BackendOfflineOverlay', () => {
  it('renders nothing when the backend is online', () => {
    useTwinStore.setState({ isBackendOffline: false });
    const { container } = render(<BackendOfflineOverlay />);
    expect(container).toBeEmptyDOMElement();
  });

  it('shows STARTING BACKEND with amber tone while waking up (wakeUpStatus=waking)', () => {
    useTwinStore.setState({ isBackendOffline: true, wakeUpStatus: 'waking', wakeUpRetries: 0 });
    render(<BackendOfflineOverlay />);

    expect(screen.getByRole('alert')).toBeInTheDocument();
    expect(screen.getByText('STARTING BACKEND')).toBeInTheDocument();
    expect(screen.getByText(/Waking up HF Space/)).toBeInTheDocument();
    // HF cold-start explainer should appear
    expect(screen.getByText(/Hugging Face free-tier Spaces sleep/)).toBeInTheDocument();
  });

  it('shows retry count inside the waking subtitle', () => {
    useTwinStore.setState({ isBackendOffline: true, wakeUpStatus: 'waking', wakeUpRetries: 3 });
    render(<BackendOfflineOverlay />);

    expect(screen.getByText(/attempt 3\/10/)).toBeInTheDocument();
  });

  it('shows BACKEND UNREACHABLE after all retries fail (wakeUpStatus=failed)', () => {
    useTwinStore.setState({ isBackendOffline: true, wakeUpStatus: 'failed', wakeUpRetries: 10 });
    render(<BackendOfflineOverlay />);

    expect(screen.getByText('BACKEND UNREACHABLE')).toBeInTheDocument();
    expect(screen.getByText(/Failed after 10 retries/)).toBeInTheDocument();
  });

  it('shows the generic BACKEND OFFLINE reconnecting message once wakeUp=ready but backend drops mid-session', () => {
    // wakeUpStatus=ready means cold-start passed; a mid-session drop shows the original message.
    useTwinStore.setState({ isBackendOffline: true, wakeUpStatus: 'ready', wakeUpRetries: 0 });
    render(<BackendOfflineOverlay />);

    expect(screen.getByText('BACKEND OFFLINE')).toBeInTheDocument();
    expect(screen.getByText(/Attempting to reconnect/)).toBeInTheDocument();
  });
});

