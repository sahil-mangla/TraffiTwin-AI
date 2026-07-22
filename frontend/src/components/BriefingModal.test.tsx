import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BriefingModal } from './BriefingModal';
import { useTwinStore } from '../store/twinStore';

beforeEach(() => {
  useTwinStore.setState(useTwinStore.getInitialState(), true);
});

afterEach(() => {
  vi.useRealTimers();
});

describe('BriefingModal', () => {
  it('renders nothing when the briefing is closed', () => {
    useTwinStore.setState({ isBriefingOpen: false });
    const { container } = render(<BriefingModal />);
    expect(container).toBeEmptyDOMElement();
  });

  it('shows the briefing dialog when open', () => {
    useTwinStore.setState({ isBriefingOpen: true });
    render(<BriefingModal />);

    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(screen.getByText('ABOUT TRAFFITWIN AI')).toBeInTheDocument();
  });

  it('dismiss button closes the briefing', async () => {
    useTwinStore.setState({ isBriefingOpen: true });
    const user = userEvent.setup();
    render(<BriefingModal />);

    await user.click(screen.getByRole('button', { name: 'Dismiss briefing' }));

    expect(useTwinStore.getState().isBriefingOpen).toBe(false);
  });

  it('"ENTER TERMINAL" button closes the briefing', async () => {
    useTwinStore.setState({ isBriefingOpen: true });
    const user = userEvent.setup();
    render(<BriefingModal />);

    await user.click(screen.getByRole('button', { name: 'ENTER TERMINAL' }));

    expect(useTwinStore.getState().isBriefingOpen).toBe(false);
  });

  it('Escape key closes the briefing', async () => {
    useTwinStore.setState({ isBriefingOpen: true });
    const user = userEvent.setup();
    render(<BriefingModal />);

    await user.keyboard('{Escape}');

    expect(useTwinStore.getState().isBriefingOpen).toBe(false);
  });

  it('auto-closes after the countdown reaches zero', async () => {
    vi.useFakeTimers();
    useTwinStore.setState({ isBriefingOpen: true });
    render(<BriefingModal />);

    // 6 ticks of the 1s countdown interval; a little extra margin avoids
    // boundary ambiguity over whether a timer firing at exactly the target
    // time is included.
    await vi.advanceTimersByTimeAsync(6500);

    expect(useTwinStore.getState().isBriefingOpen).toBe(false);
  });
});
