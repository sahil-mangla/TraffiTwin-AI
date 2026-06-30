import { useEffect, useRef } from 'react';
import { useTwinStore } from '../store/twinStore';

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

export function OperationsRail() {
  const metrics = useTwinStore((s) => s.metrics);
  const snapshot = useTwinStore((s) => s.snapshot);
  const isLoading = useTwinStore((s) => s.isLoading);
  const latestIncidentSummary = useTwinStore((s) => s.latestIncidentSummary);
  const isAnalyzing = useTwinStore((s) => s.isAnalyzing);
  const runAnalysis = useTwinStore((s) => s.runAnalysis);

  if (isLoading || !metrics || !snapshot) {
    return (
      <aside className="h-full border-l border-[#2A3545] bg-[#0B0F14] p-4 flex flex-col gap-4">
        {[...Array(3)].map((_, i) => (
          <div key={i} className="h-24 rounded-xl bg-[#121820] animate-pulse" />
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
  const obsLabel = observability >= 95 ? 'OPERATIONAL' : observability >= 90 ? 'DEGRADED' : 'CRITICAL';

  return (
    <aside
      className="h-full border-l border-[#2A3545] bg-[#0B0F14] flex flex-col overflow-hidden"
      aria-label="Operations Rail"
    >
      <div className="px-4 py-3 border-b border-[#2A3545]">
        <p className="text-[10px] font-mono text-[#8BA0BA] tracking-widest">OPERATIONS RAIL</p>
      </div>

      <div className="flex-1 overflow-y-auto p-3 flex flex-col gap-3">

        {/* ── Network Observability Hero ─────────────────────────────────── */}
        <div
          className="rounded-xl p-5 relative overflow-hidden"
          style={{
            background: 'var(--premium-card-bg)',
            border: '1px solid var(--premium-card-border)',
            boxShadow: 'var(--premium-card-shadow)',
          }}
        >
          <div className="absolute top-0 left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-[#E8EDF4]/20 to-transparent" />
          <div className="text-[11px] font-mono text-[#8BA0BA] tracking-widest mb-3">
            NETWORK OBSERVABILITY
          </div>
          <div className="text-6xl font-mono font-bold leading-none mb-1" style={{ color: obsColor }}>
            <AnimatedNumber value={observability} decimals={2} />
            <span className="text-2xl ml-1 font-normal text-[#8BA0BA]">%</span>
          </div>
          <div className="mt-3 text-sm font-mono font-bold tracking-widest" style={{ color: obsColor }}>
            {obsLabel}
          </div>

          {/* Inline sub-stats */}
          <div className="mt-4 pt-3 border-t border-[#2A3545] grid grid-cols-2 gap-x-4 gap-y-1">
            <div>
              <div className="text-[9px] font-mono text-[#8BA0BA] tracking-widest mb-0.5">RECON ACC.</div>
              <div className="text-sm font-mono font-semibold" style={{ color: metrics.fcr >= 95 ? '#10B981' : metrics.fcr >= 80 ? '#F59E0B' : '#EF4444' }}>
                {metrics.fcr.toFixed(1)}<span className="text-[10px] text-[#8BA0BA] ml-0.5">%</span>
              </div>
            </div>
            <div>
              <div className="text-[9px] font-mono text-[#8BA0BA] tracking-widest mb-0.5">SESSIONS</div>
              <div className="text-sm font-mono font-semibold text-[#8BA0BA]">
                {metrics.total_failures_simulated}
                <span className="text-[10px] ml-0.5">sim</span>
              </div>
            </div>
          </div>
        </div>

        {/* ── AI Operations Analyst ─────────────────────────────────────── */}
        <div className="flex flex-col flex-1 min-h-0">
          <p className="text-[10px] font-mono text-[#8BA0BA] tracking-widest mb-2 uppercase">
            AI Operations Analyst
          </p>
          <div
            className="rounded-xl p-3 relative overflow-hidden text-xs font-mono leading-relaxed flex-1"
            style={{
              background: 'var(--premium-card-bg)',
              border: '1px solid var(--premium-card-border)',
              boxShadow: 'var(--premium-card-shadow)',
              minHeight: '120px',
            }}
          >
            <div className="absolute top-0 left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-[#E8EDF4]/10 to-transparent" />

            {isAnalyzing ? (
              <div className="flex flex-col items-center justify-center py-6 gap-3">
                <span className="animate-spin text-xl" style={{ color: '#8B5CF6' }}>✦</span>
                <span className="text-[11px] text-[#8BA0BA]">Analyzing digital twin state…</span>
              </div>
            ) : latestIncidentSummary ? (
              <div className="flex flex-col gap-3">
                <div className="text-[#E8EDF4] break-words leading-relaxed">
                  {latestIncidentSummary}
                </div>
                <button
                  onClick={() => runAnalysis()}
                  className="w-full py-1 px-2 rounded border text-[10px] font-mono tracking-wider transition-all duration-200 cursor-pointer"
                  style={{
                    borderColor: '#8B5CF620',
                    background: 'transparent',
                    color: '#8BA0BA',
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.borderColor = '#8B5CF660';
                    e.currentTarget.style.color = '#C084FC';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.borderColor = '#8B5CF620';
                    e.currentTarget.style.color = '#8BA0BA';
                  }}
                >
                  ↺ RE-ANALYZE
                </button>
              </div>
            ) : (
              <div className="flex flex-col gap-3 items-center text-center pt-2">
                <div className="text-[#8BA0BA] italic text-[11px] leading-relaxed">
                  {activeFailed > 0
                    ? 'Anomaly detected. AI diagnostic standby.'
                    : 'System nominal. Ready for status check.'}
                </div>
                <button
                  onClick={() => runAnalysis()}
                  className="w-full py-2 px-3 rounded-lg border transition-all duration-200 cursor-pointer flex items-center justify-center gap-1.5 text-[11px] font-mono"
                  style={{
                    borderColor: '#8B5CF640',
                    background: '#8B5CF610',
                    color: '#C084FC',
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.borderColor = '#8B5CF6';
                    e.currentTarget.style.background = '#8B5CF620';
                    e.currentTarget.style.color = '#fff';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.borderColor = '#8B5CF640';
                    e.currentTarget.style.background = '#8B5CF610';
                    e.currentTarget.style.color = '#C084FC';
                  }}
                >
                  <span>✦</span>
                  <span>{activeFailed > 0 ? 'Run AI Anomaly Diagnostic' : 'Analyze System State'}</span>
                </button>
              </div>
            )}
          </div>
        </div>

      </div>
    </aside>
  );
}
