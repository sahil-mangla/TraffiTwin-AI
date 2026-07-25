import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { api } from './trafitwin';
import { useAuthStore } from '../store/authStore';

describe('trafitwin api client auth handling', () => {
  beforeEach(() => {
    useAuthStore.setState({ token: null, email: null });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('attaches an Authorization header when a token is present', async () => {
    useAuthStore.setState({ token: 'my-jwt', email: 'user@example.com' });
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ current_time: 1, message: 'ok' }),
    });
    vi.stubGlobal('fetch', fetchMock);

    await api.stepSimulation(1);

    const [, options] = fetchMock.mock.calls[0];
    expect(options.headers['Authorization']).toBe('Bearer my-jwt');
  });

  it('omits the Authorization header when logged out', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ status: 'ok', version: '1.0.0' }),
    });
    vi.stubGlobal('fetch', fetchMock);

    await api.getHealth();

    const [, options] = fetchMock.mock.calls[0];
    expect(options.headers['Authorization']).toBeUndefined();
  });

  it('logs out on a 401 response', async () => {
    useAuthStore.setState({ token: 'stale-jwt', email: 'user@example.com' });
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      status: 401,
      text: async () => 'Unauthorized',
    });
    vi.stubGlobal('fetch', fetchMock);

    await expect(api.stepSimulation(1)).rejects.toThrow();
    expect(useAuthStore.getState().token).toBeNull();
  });
});
