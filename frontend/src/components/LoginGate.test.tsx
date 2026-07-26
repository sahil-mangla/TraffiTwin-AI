import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { LoginGate } from './LoginGate';
import { useAuthStore } from '../store/authStore';
import { api } from '../api/trafitwin';

vi.mock('../api/trafitwin', () => ({
  api: {
    loginWithGoogle: vi.fn(),
  },
}));

beforeEach(() => {
  useAuthStore.setState({ token: null, email: null });
  vi.clearAllMocks();
});

describe('LoginGate', () => {
  it('renders the Google sign-in button when logged out', () => {
    render(<LoginGate />);
    expect(screen.getByLabelText('Sign in with Google')).toBeInTheDocument();
  });

  it('exchanges a successful Google credential for a session and signs the user in', async () => {
    vi.mocked(api.loginWithGoogle).mockResolvedValue({
      access_token: 'jwt-token',
      token_type: 'bearer',
      email: 'user@example.com',
    });
    const user = userEvent.setup();
    render(<LoginGate />);

    await user.click(screen.getByLabelText('Sign in with Google'));

    expect(api.loginWithGoogle).toHaveBeenCalledWith('fake-credential');
    expect(useAuthStore.getState().token).toBe('jwt-token');
    expect(useAuthStore.getState().email).toBe('user@example.com');
  });

  it('logs the error and stays logged out when the exchange fails', async () => {
    vi.mocked(api.loginWithGoogle).mockRejectedValue(new Error('network error'));
    vi.spyOn(console, 'error').mockImplementation(() => {});
    const user = userEvent.setup();
    render(<LoginGate />);

    await user.click(screen.getByLabelText('Sign in with Google'));

    expect(useAuthStore.getState().token).toBeNull();
  });

  it('shows the signed-in pill with the account email when a token is present', () => {
    useAuthStore.setState({ token: 'jwt-token', email: 'user@example.com' });
    render(<LoginGate />);

    expect(screen.getByText('user@example.com')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Sign out' })).toBeInTheDocument();
  });

  it('signs the user out when SIGN OUT is clicked', async () => {
    useAuthStore.setState({ token: 'jwt-token', email: 'user@example.com' });
    const user = userEvent.setup();
    render(<LoginGate />);

    await user.click(screen.getByRole('button', { name: 'Sign out' }));

    expect(useAuthStore.getState().token).toBeNull();
    expect(useAuthStore.getState().email).toBeNull();
  });
});
