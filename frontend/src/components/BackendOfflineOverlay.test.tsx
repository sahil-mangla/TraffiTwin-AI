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

  it('shows the offline alert when the backend goes offline', () => {
    useTwinStore.setState({ isBackendOffline: true });
    render(<BackendOfflineOverlay />);

    expect(screen.getByRole('alert')).toBeInTheDocument();
    expect(screen.getByText('BACKEND OFFLINE')).toBeInTheDocument();
  });
});
