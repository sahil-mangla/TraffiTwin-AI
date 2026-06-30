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
  return new Date(iso).toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
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
      className="flex items-start gap-2 px-3 py-2 rounded-md text-xs font-mono border shadow-sm"
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

export function EventTimeline() {
  const events = useTwinStore((s) => s.events);
  const clearEvents = useTwinStore((s) => s.clearEvents);

  return (
    <section className="flex flex-col h-full" aria-label="Event Timeline">
      <div className="flex items-center justify-between px-3 py-2 border-b border-[#2A3545] shrink-0" style={{ background: 'var(--premium-card-bg)' }}>
        <p className="text-[10px] font-mono text-[#8BA0BA] tracking-widest">EVENT LOG</p>
        {events.length > 0 && (
          <button
            onClick={clearEvents}
            className="text-[10px] font-mono text-[#8BA0BA] hover:text-[#E8EDF4] transition-colors"
            aria-label="Clear event log"
          >
            CLEAR
          </button>
        )}
      </div>

      <div className="flex-1 overflow-y-auto p-2 flex flex-col gap-1.5">
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
    </section>
  );
}
