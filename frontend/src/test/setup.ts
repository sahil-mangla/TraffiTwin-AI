import { afterEach, beforeEach, vi } from 'vitest';
import { cleanup } from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import { useAuthStore } from '../store/authStore';

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

// jsdom doesn't implement ResizeObserver (used by NetworkGraph to size its
// canvas). A no-op stub is enough for components that merely need it to
// exist; tests that care about resize behavior replace it with their own
// vi.stubGlobal('ResizeObserver', ...) mock. Re-applied every test since
// afterEach clears all stubbed globals.
class NoopResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}
beforeEach(() => {
  vi.stubGlobal('ResizeObserver', NoopResizeObserver);
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

// @react-oauth/google renders a real Google Identity Services iframe/script
// that jsdom can't load. Replace GoogleLogin with a plain button so tests
// can drive the sign-in flow via its onSuccess callback without a live
// GoogleOAuthProvider or network access.
vi.mock('@react-oauth/google', async () => {
  const React = await import('react');
  return {
    GoogleOAuthProvider: ({ children }: { children?: React.ReactNode }) => children,
    GoogleLogin: ({ onSuccess }: { onSuccess: (response: { credential: string }) => void }) =>
      React.createElement(
        'button',
        { type: 'button', 'aria-label': 'Sign in with Google', onClick: () => onSuccess({ credential: 'fake-credential' }) },
        'Sign in with Google'
      ),
  };
});
