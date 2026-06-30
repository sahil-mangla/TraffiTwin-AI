import { useEffect, useRef, useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { useTwinStore, type AnalysisCard, type AnalysisSource } from '../store/twinStore';

// ── Animated Number Counter ───────────────────────────────────────────────────
function AnimatedNumber({ value, decimals = 2 }: { value: number; decimals?: number }) {
  const ref = useRef<HTMLSpanElement>(null);
  const prevRef = useRef(value);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const start = prevRef.current;
    const end = value;
    const dur = 400;
    const startTime = performance.now();

    function tick(now: number) {
      if (!ref.current) return;
      const t = Math.min((now - startTime) / dur, 1);
      const eased = 1 - (1 - t) * (1 - t);
      const current = start + (end - start) * eased;
      ref.current.textContent = current.toFixed(decimals);
      if (t < 1) requestAnimationFrame(tick);
      else prevRef.current = end;
    }
    requestAnimationFrame(tick);
  }, [value, decimals]);

  return <span ref={ref}>{value.toFixed(decimals)}</span>;
}

// ── Source Label Map ─────────────────────────────────────────────────────────
const SOURCE_LABELS: Record<AnalysisSource, string> = {
  analyze_system_state: 'SYS-STATE',
  current_failures: 'FAILURES',
  recent_incidents: 'INCIDENTS',
  performance_metrics: 'METRICS',
  custom_query: 'CUSTOM',
};

const SOURCE_COLORS: Record<AnalysisSource, string> = {
  analyze_system_state: '#3B82F6',
  current_failures: '#EF4444',
  recent_incidents: '#F59E0B',
  performance_metrics: '#10B981',
  custom_query: '#8B5CF6',
};

// ── Format Timestamp ─────────────────────────────────────────────────────────
function formatTimestamp(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

// ── Analysis Card ─────────────────────────────────────────────────────────────
function AnalysisCardItem({ card }: { card: AnalysisCard }) {
  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: -12, scale: 0.97 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, scale: 0.96, transition: { duration: 0.15 } }}
      transition={{ type: 'spring', stiffness: 380, damping: 35 }}
      className="rounded-lg overflow-hidden flex-shrink-0"
      style={{
        background: 'linear-gradient(180deg, rgba(26,34,48,0.98), rgba(18,24,32,0.98))',
        border: '1px solid rgba(255,255,255,0.07)',
        boxShadow: '0 4px 16px rgba(0,0,0,0.3)',
      }}
    >
      {/* Card header */}
      <div
        className="px-3 py-2 flex items-center justify-between gap-2"
        style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}
      >
        <div className="flex items-center gap-2 min-w-0">
          <span
            className="w-1.5 h-1.5 rounded-full flex-shrink-0"
            style={{ background: '#10B981', boxShadow: '0 0 4px #10B981' }}
          />
          <span className="text-[10px] font-mono font-semibold text-[#E8EDF4] truncate">
            {card.title}
          </span>
        </div>
        <span className="text-[9px] font-mono text-[#8BA0BA] flex-shrink-0">
          {formatTimestamp(card.timestamp)}
        </span>
      </div>

      {/* Response text */}
      <div className="px-3 py-2.5">
        <p className="text-[11px] leading-relaxed text-[#C8D8E8] font-mono">
          {card.response}
        </p>
      </div>

      {/* Sources footer */}
      <div
        className="px-3 py-1.5 flex items-center gap-1.5 flex-wrap"
        style={{ borderTop: '1px solid rgba(255,255,255,0.04)' }}
      >
        <span className="text-[9px] font-mono text-[#4A5568] mr-1">DATA SOURCE</span>
        {card.sources.map((src) => (
          <span
            key={src}
            className="text-[9px] font-mono px-1.5 py-0.5 rounded"
            style={{
              color: SOURCE_COLORS[src],
              background: `${SOURCE_COLORS[src]}18`,
              border: `1px solid ${SOURCE_COLORS[src]}35`,
            }}
          >
            {SOURCE_LABELS[src]}
          </span>
        ))}
      </div>
    </motion.div>
  );
}

// ── Loading Pulse ─────────────────────────────────────────────────────────────
function AnalyzingIndicator() {
  return (
    <motion.div
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      transition={{ duration: 0.2 }}
      className="rounded-lg px-3 py-3 flex items-center gap-3 flex-shrink-0"
      style={{
        background: 'linear-gradient(180deg, rgba(139,92,246,0.08), rgba(139,92,246,0.04))',
        border: '1px solid rgba(139,92,246,0.2)',
      }}
    >
      <motion.span
        animate={{ rotate: 360 }}
        transition={{ repeat: Infinity, duration: 1.2, ease: 'linear' }}
        className="text-sm flex-shrink-0"
        style={{ color: '#8B5CF6' }}
      >
        ✦
      </motion.span>
      <div>
        <p className="text-[10px] font-mono text-[#8B5CF6] font-semibold tracking-wider">
          ANALYZING…
        </p>
        <p className="text-[9px] font-mono text-[#6B7280] mt-0.5">
          Querying digital twin state
        </p>
      </div>
    </motion.div>
  );
}

// ── Quick Action Button ───────────────────────────────────────────────────────
function QuickActionBtn({
  label,
  icon,
  action,
  color,
  onAction,
  disabled,
}: {
  label: string;
  icon: string;
  action: AnalysisSource;
  color: string;
  onAction: (a: AnalysisSource) => void;
  disabled: boolean;
}) {
  const [hovered, setHovered] = useState(false);

  return (
    <button
      onClick={() => onAction(action)}
      disabled={disabled}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-[10px] font-mono font-semibold tracking-wider transition-all duration-150 cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
      style={{
        background: hovered && !disabled ? `${color}18` : 'rgba(255,255,255,0.03)',
        border: `1px solid ${hovered && !disabled ? color + '50' : 'rgba(255,255,255,0.08)'}`,
        color: hovered && !disabled ? color : '#8BA0BA',
      }}
    >
      <span style={{ fontSize: '11px' }}>{icon}</span>
      {label}
    </button>
  );
}

// ── Suggestion Chip ───────────────────────────────────────────────────────────
function SuggestionChip({
  label,
  onSelect,
  disabled,
}: {
  label: string;
  onSelect: (q: string) => void;
  disabled: boolean;
}) {
  return (
    <button
      onClick={() => onSelect(label)}
      disabled={disabled}
      className="text-[10px] font-mono px-2 py-1 rounded-full border transition-all duration-150 cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed text-left whitespace-nowrap"
      style={{
        borderColor: 'rgba(59,130,246,0.25)',
        background: 'rgba(59,130,246,0.06)',
        color: '#FFFFFF',
      }}
      onMouseEnter={(e) => {
        if (!disabled) {
          e.currentTarget.style.borderColor = 'rgba(59,130,246,0.6)';
          e.currentTarget.style.color = '#93C5FD';
          e.currentTarget.style.background = 'rgba(59,130,246,0.12)';
        }
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.borderColor = 'rgba(59,130,246,0.25)';
        e.currentTarget.style.color = '#8BA0BA';
        e.currentTarget.style.background = 'rgba(59,130,246,0.06)';
      }}
    >
      {label}
    </button>
  );
}

// ── Main Component ────────────────────────────────────────────────────────────
export function OperationsRail() {
  const metrics = useTwinStore((s) => s.metrics);
  const snapshot = useTwinStore((s) => s.snapshot);
  const isLoading = useTwinStore((s) => s.isLoading);
  const isAnalyzing = useTwinStore((s) => s.isAnalyzing);
  const analysisFeed = useTwinStore((s) => s.analysisFeed);
  const runQuickAction = useTwinStore((s) => s.runQuickAction);

  const [customQuery, setCustomQuery] = useState('');
  const feedRef = useRef<HTMLDivElement>(null);

  const handleQuickAction = useCallback(
    (action: AnalysisSource) => {
      if (!isAnalyzing) runQuickAction(action);
    },
    [isAnalyzing, runQuickAction]
  );

  const handleSuggestion = useCallback(
    (q: string) => {
      if (!isAnalyzing) runQuickAction('custom_query', q);
    },
    [isAnalyzing, runQuickAction]
  );

  const handleCustomSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      const q = customQuery.trim();
      if (!q || isAnalyzing) return;
      runQuickAction('custom_query', q);
      setCustomQuery('');
    },
    [customQuery, isAnalyzing, runQuickAction]
  );

  if (isLoading || !metrics || !snapshot) {
    return (
      <aside className="h-full border-l border-[#2A3545] bg-[#0B0F14] p-4 flex flex-col gap-4">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="h-20 rounded-xl bg-[#121820] animate-pulse" />
        ))}
      </aside>
    );
  }

  const totalSensors = Object.keys(snapshot.readings).length || 207;
  const activeFailed = Object.values(snapshot.masks).filter(Boolean).length;
  const activeRecon = Object.keys(snapshot.reconstructions).length;
  const observability = ((totalSensors - activeFailed + activeRecon) / totalSensors) * 100;
  const obsStatus = observability >= 95 ? 'ok' : observability >= 90 ? 'warn' : 'fail';
  const obsColor = obsStatus === 'ok' ? '#10B981' : obsStatus === 'warn' ? '#F59E0B' : '#EF4444';

  return (
    <aside
      className="h-full border-l border-[#2A3545] bg-[#0B0F14] flex flex-col overflow-hidden"
      aria-label="Operations Intelligence Rail"
    >
      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <div className="px-4 py-3 border-b border-[#2A3545] flex-shrink-0">
        <p className="text-[10px] font-mono text-[#8BA0BA] tracking-widest">
          OPS INTELLIGENCE
        </p>
      </div>

      {/* ── Scrollable body ────────────────────────────────────────────────── */}
      <div className="flex-1 overflow-y-auto p-3 flex flex-col gap-3 min-h-0">

        {/* ── Network Observability Hero ──────────────────────────────────── */}
        <div
          className="rounded-xl p-4 relative overflow-hidden flex-shrink-0"
          style={{
            background: 'var(--premium-card-bg)',
            border: '1px solid var(--premium-card-border)',
            boxShadow: 'var(--premium-card-shadow)',
          }}
        >
          <div className="absolute top-0 left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-[#E8EDF4]/20 to-transparent" />
          <div className="text-[10px] font-mono text-[#8BA0BA] tracking-widest mb-2">
            NETWORK OBSERVABILITY
          </div>
          <div className="flex items-end justify-between">
            <div className="text-5xl font-mono font-bold leading-none" style={{ color: obsColor }}>
              <AnimatedNumber value={observability} decimals={2} />
              <span className="text-xl ml-1 font-normal text-[#8BA0BA]">%</span>
            </div>
          </div>
          <div className="mt-3 pt-2.5 border-t border-[#2A3545] grid grid-cols-2 gap-2">
            <div>
              <div className="text-[8px] font-mono text-[#8BA0BA] tracking-widest mb-0.5">MAE</div>
              <div className="text-xs font-mono font-semibold text-[#E8EDF4]">{metrics.mae.toFixed(2)}</div>
            </div>
            <div>
              <div className="text-[8px] font-mono text-[#8BA0BA] tracking-widest mb-0.5">SIM OPS</div>
              <div className="text-xs font-mono font-semibold text-[#8BA0BA]">{metrics.total_failures_simulated}</div>
            </div>
          </div>
        </div>

        {/* ── Quick Actions ───────────────────────────────────────────────── */}
        <div className="flex-shrink-0">
          <p className="text-[9px] font-mono text-[#FFFFFF] tracking-widest mb-1.5 uppercase">
            Quick Actions
          </p>
          <div className="grid grid-cols-2 gap-1.5">
            <QuickActionBtn
              label="System State"
              icon="⬡"
              action="analyze_system_state"
              color="#3B82F6"
              onAction={handleQuickAction}
              disabled={isAnalyzing}
            />
            <QuickActionBtn
              label="Failures"
              icon="⚠"
              action="current_failures"
              color="#EF4444"
              onAction={handleQuickAction}
              disabled={isAnalyzing}
            />
            <QuickActionBtn
              label="Incidents"
              icon="◈"
              action="recent_incidents"
              color="#F59E0B"
              onAction={handleQuickAction}
              disabled={isAnalyzing}
            />
            <QuickActionBtn
              label="Metrics"
              icon="◎"
              action="performance_metrics"
              color="#10B981"
              onAction={handleQuickAction}
              disabled={isAnalyzing}
            />
          </div>
        </div>

        {/* ── Suggested Questions ─────────────────────────────────────────── */}
        <div className="flex-shrink-0">
          <p className="text-[9px] font-mono text-[#FFFFFF] tracking-widest mb-1.5 uppercase">
            Suggested
          </p>
          <div className="flex flex-wrap gap-1">
            {[
              'What is happening right now?',
              'Is the network operational?',
              'Which sensors are offline?',
              'Summarize recent incidents.',
            ].map((q) => (
              <SuggestionChip
                key={q}
                label={q}
                onSelect={handleSuggestion}
                disabled={isAnalyzing}
              />
            ))}
          </div>
        </div>

        {/* ── Analysis Feed ───────────────────────────────────────────────── */}
        <div className="flex flex-col flex-shrink-0">
          <div className="flex items-center justify-between mb-1.5">
            <p className="text-[9px] font-mono text-[#FFFFFF] tracking-widest uppercase">
              Analysis Feed
            </p>
            {analysisFeed.length > 0 && (
              <span className="text-[8px] font-mono text-[#2A3545]">
                {analysisFeed.length}/20
              </span>
            )}
          </div>

          <div
            ref={feedRef}
            className="flex flex-col gap-2 overflow-y-auto scroll-smooth"
            style={{ height: '420px' }}
          >
            <AnimatePresence mode="popLayout" initial={false}>
              {isAnalyzing && <AnalyzingIndicator key="analyzing" />}

              {analysisFeed.length === 0 && !isAnalyzing && (
                <motion.div
                  key="empty"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="flex flex-col items-center justify-center h-full gap-2 text-center py-8"
                >
                  <div
                    className="w-10 h-10 rounded-full flex items-center justify-center"
                    style={{ background: 'rgba(59,130,246,0.08)', border: '1px solid rgba(59,130,246,0.15)' }}
                  >
                    <span className="text-lg" style={{ color: '#3B82F640' }}>⬡</span>
                  </div>
                  <p className="text-[10px] font-mono text-[#FFFFFF] leading-relaxed">
                    No analyses yet.<br />Run an action above.
                  </p>
                </motion.div>
              )}

              {analysisFeed.map((card) => (
                <AnalysisCardItem key={card.id} card={card} />
              ))}
            </AnimatePresence>
          </div>
        </div>

      </div>

      {/* ── Custom Query Input ─────────────────────────────────────────────── */}
      <div
        className="px-3 py-2.5 flex-shrink-0"
        style={{ borderTop: '1px solid #2A3545' }}
      >
        <form onSubmit={handleCustomSubmit} className="flex gap-2 items-center">
          <input
            type="text"
            value={customQuery}
            onChange={(e) => setCustomQuery(e.target.value)}
            placeholder="Ask the analyst…"
            disabled={isAnalyzing}
            className="flex-1 bg-transparent text-[11px] font-mono text-[#FFFFFF] placeholder-[rgba(255,255,255,0.45)] outline-none disabled:opacity-40"
            style={{
              background: 'rgba(255,255,255,0.03)',
              border: '1px solid rgba(255,255,255,0.06)',
              borderRadius: '6px',
              padding: '6px 10px',
            }}
            onFocus={(e) => {
              e.currentTarget.style.borderColor = 'rgba(139,92,246,0.4)';
            }}
            onBlur={(e) => {
              e.currentTarget.style.borderColor = 'rgba(255,255,255,0.06)';
            }}
          />
          <button
            type="submit"
            disabled={isAnalyzing || !customQuery.trim()}
            className="flex-shrink-0 w-7 h-7 rounded-lg flex items-center justify-center transition-all duration-150 cursor-pointer disabled:opacity-65 disabled:cursor-not-allowed"
            style={{
              background: customQuery.trim() && !isAnalyzing ? 'rgba(139,92,246,0.2)' : 'rgba(255,255,255,0.04)',
              border: `1px solid ${customQuery.trim() && !isAnalyzing ? 'rgba(139,92,246,0.5)' : 'rgba(255,255,255,0.12)'}`,
            }}
          >
            <span className="text-[11px]" style={{ color: customQuery.trim() && !isAnalyzing ? '#C084FC' : '#FFFFFF' }}>
              ↑
            </span>
          </button>
        </form>
      </div>
    </aside>
  );
}
