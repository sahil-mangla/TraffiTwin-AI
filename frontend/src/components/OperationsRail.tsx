import { useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'motion/react';
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
      const t = Math.min((now - startTime) / dur, 1);
      const eased = 1 - (1 - t) * (1 - t); // ease-out-quad
      const current = start + (end - start) * eased;
      el.textContent = current.toFixed(decimals);
      if (t < 1) requestAnimationFrame(tick);
      else prevRef.current = end;
    }
    requestAnimationFrame(tick);
  }, [value, decimals]);

  return <span ref={ref}>{value.toFixed(decimals)}</span>;
}

function MetricCard({
  label,
  value,
  unit,
  sub,
  accent,
  large,
  status,
}: {
  label: string;
  value: number;
  unit?: string;
  sub?: string;
  accent?: string;
  large?: boolean;
  status?: 'ok' | 'warn' | 'fail';
}) {
  const statusColor = { ok: '#10B981', warn: '#F59E0B', fail: '#EF4444' }[status ?? 'ok'];

  return (
    <div className="rounded border border-[#2A3545] bg-[#121820] p-3">
      <div className="text-[10px] font-mono text-[#8BA0BA] tracking-widest mb-1 uppercase">{label}</div>
      <div className={`font-mono font-bold leading-none ${large ? 'text-4xl' : 'text-2xl'}`}
        style={{ color: accent ?? statusColor }}>
        <AnimatedNumber value={value} decimals={large ? 2 : 2} />
        {unit && <span className="text-sm ml-1 font-normal text-[#8BA0BA]">{unit}</span>}
      </div>
      {sub && <div className="text-[11px] font-mono mt-1" style={{ color: statusColor }}>{sub}</div>}
    </div>
  );
}

export function OperationsRail() {
  const metrics = useTwinStore((s) => s.metrics);
  const snapshot = useTwinStore((s) => s.snapshot);
  const isLoading = useTwinStore((s) => s.isLoading);

  if (isLoading || !metrics || !snapshot) {
    return (
      <aside className="h-full border-l border-[#2A3545] bg-[#0B0F14] p-4 flex flex-col gap-3">
        {[...Array(6)].map((_, i) => (
          <div key={i} className="h-16 rounded bg-[#121820] animate-pulse" />
        ))}
      </aside>
    );
  }

  const activeFailed = Object.values(snapshot.masks).filter(Boolean).length;
  const activeRecon = Object.keys(snapshot.reconstructions).length;
  const fcrStatus = metrics.fcr >= 95 ? 'ok' : metrics.fcr >= 80 ? 'warn' : 'fail';
  const fcrLabel = metrics.fcr >= 95 ? 'OPERATIONAL' : metrics.fcr >= 80 ? 'DEGRADED' : 'CRITICAL';

  return (
    <aside
      className="h-full border-l border-[#2A3545] bg-[#0B0F14] flex flex-col overflow-hidden"
      aria-label="Operations Rail"
    >
      <div className="px-4 py-3 border-b border-[#2A3545]">
        <p className="text-[10px] font-mono text-[#8BA0BA] tracking-widest">OPERATIONS RAIL</p>
      </div>

      <div className="flex-1 overflow-y-auto p-3 flex flex-col gap-3">
        {/* Hero metric */}
        <div className="rounded border border-[#2A3545] bg-[#1A2230] p-4">
          <div className="text-[10px] font-mono text-[#8BA0BA] tracking-widest mb-2">
            NETWORK OBSERVABILITY — FCR
          </div>
          <div className="text-5xl font-mono font-bold leading-none"
            style={{ color: fcrStatus === 'ok' ? '#10B981' : fcrStatus === 'warn' ? '#F59E0B' : '#EF4444' }}>
            <AnimatedNumber value={metrics.fcr} decimals={2} />
            <span className="text-xl ml-1 font-normal text-[#8BA0BA]">%</span>
          </div>
          <div className="mt-2 text-xs font-mono font-semibold tracking-widest"
            style={{ color: fcrStatus === 'ok' ? '#10B981' : fcrStatus === 'warn' ? '#F59E0B' : '#EF4444' }}>
            {fcrLabel}
          </div>
        </div>

        {/* Secondary metrics grid */}
        <div className="grid grid-cols-2 gap-2">
          <MetricCard label="MAE" value={metrics.mae} unit="mph" status="ok" />
          <MetricCard label="RMSE" value={metrics.rmse} unit="mph" status="ok" />
          <MetricCard
            label="Active Failures"
            value={activeFailed}
            accent={activeFailed > 0 ? '#EF4444' : '#10B981'}
            status={activeFailed > 0 ? 'fail' : 'ok'}
          />
          <MetricCard
            label="AI Reconstructed"
            value={activeRecon}
            accent={activeRecon > 0 ? '#8B5CF6' : '#8BA0BA'}
          />
        </div>

        <MetricCard
          label="Total Failures Simulated"
          value={metrics.total_failures_simulated}
          decimals={0}
          accent="#8BA0BA"
        />

        {/* Divider */}
        <div className="border-t border-[#2A3545] pt-2">
          <p className="text-[10px] font-mono text-[#8BA0BA] tracking-widest mb-2">SYSTEM ALERTS</p>
          <AlertItems activeFailed={activeFailed} activeRecon={activeRecon} />
        </div>
      </div>
    </aside>
  );
}

function AlertItems({ activeFailed, activeRecon }: { activeFailed: number; activeRecon: number }) {
  const alerts = [];
  if (activeFailed > 0) {
    alerts.push({
      id: 'fail',
      icon: '⚠',
      text: `${activeFailed} sensor${activeFailed > 1 ? 's' : ''} offline`,
      color: '#EF4444',
    });
  }
  if (activeRecon > 0) {
    alerts.push({
      id: 'recon',
      icon: '✦',
      text: `AI reconstructing ${activeRecon} sensor${activeRecon > 1 ? 's' : ''}`,
      color: '#8B5CF6',
    });
  }
  if (alerts.length === 0) {
    alerts.push({ id: 'ok', icon: '✓', text: 'All sensors nominal', color: '#10B981' });
  }

  return (
    <div className="flex flex-col gap-1.5">
      <AnimatePresence mode="popLayout">
        {alerts.map((a) => (
          <motion.div
            key={a.id}
            initial={{ opacity: 0, x: 8 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -8 }}
            transition={{ duration: 0.2 }}
            className="flex items-center gap-2 rounded px-2 py-1.5 text-xs font-mono"
            style={{ backgroundColor: a.color + '15', color: a.color, border: `1px solid ${a.color}33` }}
          >
            <span>{a.icon}</span>
            <span>{a.text}</span>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}

