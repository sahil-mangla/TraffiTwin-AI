import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { StorytellingBanner } from './StorytellingBanner';
import { useTwinStore } from '../store/twinStore';

beforeEach(() => {
  useTwinStore.setState(useTwinStore.getInitialState(), true);
});

describe('StorytellingBanner', () => {
  it('renders nothing when there is no active banner', () => {
    const { container } = render(<StorytellingBanner />);
    expect(container).toBeEmptyDOMElement();
  });

  it('renders a fault banner with its message and subtitle', () => {
    useTwinStore.setState({
      activeBanner: { type: 'fault', message: 'SENSOR FAILURE DETECTED', subtitle: 'Sensor 5 offline' },
    });
    render(<StorytellingBanner />);

    const alert = screen.getByRole('alert');
    expect(alert).toBeInTheDocument();
    expect(screen.getByText('SENSOR FAILURE DETECTED')).toBeInTheDocument();
    expect(screen.getByText('Sensor 5 offline')).toBeInTheDocument();
  });

  it('renders an AI reconstruction banner without a progress bar', () => {
    useTwinStore.setState({
      activeBanner: { type: 'ai', message: 'AI RECONSTRUCTION ENGAGED' },
    });
    render(<StorytellingBanner />);

    expect(screen.getByText('AI RECONSTRUCTION ENGAGED')).toBeInTheDocument();
  });

  it('renders a recovery banner', () => {
    useTwinStore.setState({
      activeBanner: { type: 'recovery', message: 'TRAFFIC INTELLIGENCE RESTORED', subtitle: 'Network fully observable' },
    });
    render(<StorytellingBanner />);

    expect(screen.getByText('TRAFFIC INTELLIGENCE RESTORED')).toBeInTheDocument();
  });

  it('dismisses the banner when clicked', async () => {
    useTwinStore.setState({
      activeBanner: { type: 'fault', message: 'SENSOR FAILURE DETECTED' },
    });
    const user = userEvent.setup();
    render(<StorytellingBanner />);

    await user.click(screen.getByRole('alert'));

    expect(useTwinStore.getState().activeBanner).toBeNull();
  });
});
