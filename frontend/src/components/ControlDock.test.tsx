import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ControlDock } from './ControlDock';
import { useTwinStore } from '../store/twinStore';
import { api } from '../api/trafitwin';

vi.mock('../api/trafitwin', () => ({
  api: {
    stepSimulation: vi.fn(),
    injectFailure: vi.fn(),
  },
}));

beforeEach(() => {
  useTwinStore.setState(useTwinStore.getInitialState(), true);
  vi.clearAllMocks();
});

describe('ControlDock', () => {
  it('STEP button advances the simulation and calls onStep', async () => {
    vi.mocked(api.stepSimulation).mockResolvedValue({ current_time: 1, message: 'ok' });
    const onStep = vi.fn();
    const user = userEvent.setup();
    render(<ControlDock onStep={onStep} />);

    await user.click(screen.getByRole('button', { name: 'Step simulation by one time step' }));

    expect(api.stepSimulation).toHaveBeenCalledWith(1);
    await waitFor(() => expect(onStep).toHaveBeenCalled());
  });

  it('AUTO PLAY button toggles the store autoplay flag', async () => {
    const user = userEvent.setup();
    render(<ControlDock onStep={vi.fn()} />);

    const toggle = screen.getByRole('button', { name: 'Start auto play' });
    await user.click(toggle);

    expect(useTwinStore.getState().isAutoplay).toBe(true);
  });

  it('STEP button is disabled while autoplay is active', () => {
    useTwinStore.setState({ isAutoplay: true });
    render(<ControlDock onStep={vi.fn()} />);

    expect(screen.getByRole('button', { name: 'Step simulation by one time step' })).toBeDisabled();
  });

  it('CLEAR LOG button clears the event timeline', async () => {
    useTwinStore.setState({ events: [{ id: '1', timestamp: new Date().toISOString(), severity: 'SYSTEM', message: 'x' }] });
    const user = userEvent.setup();
    render(<ControlDock onStep={vi.fn()} />);

    await user.click(screen.getByRole('button', { name: 'Clear event timeline' }));

    expect(useTwinStore.getState().events).toEqual([]);
  });

  it('INJECT FAILURE opens the modal, and submitting a valid failure injects it and adds an event', async () => {
    vi.mocked(api.injectFailure).mockResolvedValue({ status: 'success', message: 'ok' });
    const onStep = vi.fn();
    const user = userEvent.setup();
    render(<ControlDock onStep={onStep} />);

    await user.click(screen.getByRole('button', { name: 'Inject sensor failure' }));
    const dialog = screen.getByRole('dialog', { name: 'INJECT SENSOR FAILURE' });

    const inputs = dialog.querySelectorAll('input');
    fireEvent.change(inputs[0], { target: { value: '42' } });
    fireEvent.change(inputs[1], { target: { value: '5' } });

    await user.click(screen.getByRole('button', { name: 'INJECT' }));

    await waitFor(() => expect(api.injectFailure).toHaveBeenCalledWith(42, 5));
    expect(useTwinStore.getState().events[0].message).toContain('Manual failure injected on Sensor 42');
    expect(onStep).toHaveBeenCalled();
  });

  it('rejects a blank sensor ID without calling the API', async () => {
    const user = userEvent.setup();
    render(<ControlDock onStep={vi.fn()} />);

    await user.click(screen.getByRole('button', { name: 'Inject sensor failure' }));
    const dialog = screen.getByRole('dialog', { name: 'INJECT SENSOR FAILURE' });
    const inputs = dialog.querySelectorAll('input');
    // A value like 999 would violate the input's native max=206 constraint
    // and jsdom blocks the submit event before our own validation runs, so
    // an empty (non-required) field is used to exercise the app-level check.
    fireEvent.change(inputs[0], { target: { value: '' } });

    await user.click(screen.getByRole('button', { name: 'INJECT' }));

    expect(screen.getByText('Sensor ID must be 0–206')).toBeInTheDocument();
    expect(api.injectFailure).not.toHaveBeenCalled();
  });

  it('CANCEL closes the inject-failure modal without submitting', async () => {
    const user = userEvent.setup();
    render(<ControlDock onStep={vi.fn()} />);

    await user.click(screen.getByRole('button', { name: 'Inject sensor failure' }));
    await user.click(screen.getByRole('button', { name: 'CANCEL' }));

    expect(screen.queryByRole('dialog', { name: 'INJECT SENSOR FAILURE' })).not.toBeInTheDocument();
    expect(api.injectFailure).not.toHaveBeenCalled();
  });
});
