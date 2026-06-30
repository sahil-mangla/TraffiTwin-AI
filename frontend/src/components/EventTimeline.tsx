import { useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { useTwinStore } from '../store/twinStore';
import type { TwinEvent, EventSeverity } from '../types/api';

const SEVERITY_STYLES: Record<EventSeverity, { icon: string; color: string; bg: string; label: string }> = {
  FAULT:       { icon: '⚠', color: '#EF4444', bg: '#EF444415', label: 'FAULT' },
  AI_RESPONSE: { icon: '✦', color: '#8B5CF6', bg: '#8B5CF615', label: 'AI' },
  RECOVERY:    { icon: '✓', color: '#10B981', bg: '#10B98115', label: 'RECOVERY' },
  SYSTEM:      { icon: '◉', color: '#8BA0BA', bg: '#8BA0BA10', label: 'SYSTEM' },
};

function formatTime(iso: string) {
  return new Date(iso).toLocaleTimeString('en-US', {
    hour12: false,
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}

function EventRow({ event }: { event: TwinEvent }) {
  const s = SEVERITY_STYLES[event.severity];
  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: -6 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, x: -10 }}
      transition={{ duration: 0.18, ease: 'easeOut' }}
      className="flex items-start gap-2 px-3 py-2 rounded-md text-xs font-mono border shadow-sm shrink-0"
      style={{
        backgroundColor: s.bg,
        borderColor: s.color + '33',
      }}
    >
      <span style={{ color: s.color }} className="shrink-0 mt-0.5">{s.icon}</span>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-0.5">
          <span className="font-semibold tracking-wider text-[10px]" style={{ color: s.color }}>{s.label}</span>
          <span className="text-[#2A3545]">·</span>
          <span className="text-[#8BA0BA] text-[10px]">{formatTime(event.timestamp)}</span>
        </div>
        <div className="text-[#E8EDF4] truncate">{event.message}</div>
      </div>
    </motion.div>
  );
}

/**
 * EventLogDrawer — DustShield-style collapsible overlay.
 * Renders a slim toggle bar anchored to the bottom of the graph container.
 * Clicking expands an event list upward as an overlay (doesn't push the graph).
 */
export function EventLogDrawer() {
  const events = useTwinStore((s) => s.events);
  const clearEvents = useTwinStore((s) => s.clearEvents);
  const [open, setOpen] = useState(false);

  const faultCount = events.filter((e) => e.severity === 'FAULT').length;
  const hasNew = events.length > 0;

  return (
    <div className="absolute bottom-0 left-0 right-0 z-20 flex flex-col" aria-label="Event Log">
      {/* Expanded panel — slides up above the toggle bar */}
      <AnimatePresence>
        {open && (
          <motion.div
            key="drawer"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 220, opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25, ease: 'easeInOut' }}
            className="overflow-hidden"
            style={{
              background: 'rgba(11, 15, 20, 0.93)',
              backdropFilter: 'blur(12px)',
              borderTop: '1px solid #2A3545',
              boxShadow: '0 -8px 32px rgba(0,0,0,0.4)',
            }}
          >
            <div className="h-full overflow-y-auto p-2 flex flex-col gap-1.5">
              {events.length === 0 ? (
                <div className="text-[11px] font-mono text-[#2A3545] italic p-2">No events recorded.</div>
              ) : (
                <AnimatePresence mode="popLayout" initial={false}>
                  {events.map((evt) => (
                    <EventRow key={evt.id} event={evt} />
                  ))}
                </AnimatePresence>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Toggle bar — always visible at the bottom */}
      <div
        className="flex items-center justify-between px-4 py-2 cursor-pointer select-none transition-colors"
        style={{
          background: open ? 'rgba(18, 24, 32, 0.97)' : 'rgba(11, 15, 20, 0.88)',
          backdropFilter: 'blur(8px)',
          borderTop: '1px solid #2A3545',
        }}
        onClick={() => setOpen((v) => !v)}
        role="button"
        aria-expanded={open}
        aria-controls="event-log-content"
      >
        <div className="flex items-center gap-2">
          {/* Live dot */}
          <span
            className={`w-1.5 h-1.5 rounded-full ${hasNew ? 'animate-pulse' : ''}`}
            style={{ background: faultCount > 0 ? '#EF4444' : hasNew ? '#10B981' : '#2A3545' }}
          />
          <span className="text-[10px] font-mono text-[#8BA0BA] tracking-widest">EVENT LOG</span>
          {events.length > 0 && (
            <span
              className="text-[9px] font-mono px-1.5 py-0.5 rounded-full"
              style={{
                background: faultCount > 0 ? '#EF444420' : '#10B98120',
                color: faultCount > 0 ? '#EF4444' : '#10B981',
                border: `1px solid ${faultCount > 0 ? '#EF444440' : '#10B98140'}`,
              }}
            >
              {events.length}
            </span>
          )}
        </div>

        <div className="flex items-center gap-3">
          {events.length > 0 && open && (
            <button
              onClick={(e) => { e.stopPropagation(); clearEvents(); }}
              className="text-[10px] font-mono text-[#8BA0BA] hover:text-[#EF4444] transition-colors"
              aria-label="Clear event log"
            >
              CLEAR
            </button>
          )}
          <span className="text-[#8BA0BA] text-xs font-mono transition-transform duration-200" style={{ transform: open ? 'rotate(180deg)' : 'rotate(0deg)' }}>
            ▲
          </span>
        </div>
      </div>
    </div>
  );
}
