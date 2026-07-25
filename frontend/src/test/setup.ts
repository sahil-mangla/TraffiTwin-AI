import { afterEach, beforeEach, vi } from 'vitest';
import { cleanup } from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import { useAuthStore } from '../store/authStore';

afterEach(() => {
  cleanup();
});

// Most component tests exercise the "happy path" of controls that are now
// gated behind auth (STEP, AUTO PLAY, INJECT FAILURE, AI analysis actions).
// Default every test to a signed-in state so existing tests don't need to
// know about auth; tests specifically covering the logged-out/disabled
// state opt out with useAuthStore.setState({ token: null }).
beforeEach(() => {
  useAuthStore.setState({ token: 'test-token', email: 'test@example.com' });
});

// jsdom has no real animation frames, so framer-motion/`motion` exit
// animations never complete and AnimatePresence never unmounts its children.
// Replace it with a passthrough so components mount/unmount exactly per
// React's normal conditional-rendering rules — matching what tests expect.
vi.mock('motion/react', async () => {
  const React = await import('react');

  const stripMotionProps = (props: Record<string, unknown>) => {
    const {
      initial: _initial, animate: _animate, exit: _exit, transition: _transition,
      variants: _variants, layout: _layout, layoutId: _layoutId,
      whileHover: _whileHover, whileTap: _whileTap, whileFocus: _whileFocus,
      whileDrag: _whileDrag, whileInView: _whileInView,
      onAnimationStart: _onAnimationStart, onAnimationComplete: _onAnimationComplete,
      ...rest
    } = props;
    return rest;
  };

  const motion = new Proxy(
    {},
    {
      get: (_target, tag: string) =>
        React.forwardRef((props: Record<string, unknown>, ref: React.Ref<unknown>) =>
          React.createElement(tag, { ...stripMotionProps(props), ref })
        ),
    }
  );

  return {
    motion,
    AnimatePresence: ({ children }: { children?: React.ReactNode }) => children,
  };
});
