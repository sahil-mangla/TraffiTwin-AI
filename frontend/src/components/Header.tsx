import { motion, AnimatePresence } from 'motion/react';
import { useTwinStore } from '../store/twinStore';

function StatPill({
  label,
  value,
  color,
  dot,
}: {
  label: string;
  value: string | number;
  color: string;
  dot?: boolean;
}) {
  return (
    <div className="flex flex-col items-center" style={{ minWidth: '56px' }}>
      <div className="flex items-center gap-1">
        {dot && <span className="w-1.5 h-1.5 rounded-full shrink-0" style={{ background: color }} />}
        <span className="text-sm font-mono font-bold leading-none" style={{ color }}>
          {value}
        </span>
      </div>
      <span className="text-[9px] font-mono text-[#8BA0BA] tracking-widest mt-0.5 uppercase whitespace-nowrap">
        {label}
      </span>
    </div>
  );
}

export function Header() {
  const systemHealth = useTwinStore((s) => s.systemHealth);
  const snapshot = useTwinStore((s) => s.snapshot);
  const metrics = useTwinStore((s) => s.metrics);
  const openBriefing = useTwinStore((s) => s.openBriefing);

  const healthColor = {
    healthy: '#10B981',
    degraded: '#F59E0B',
    critical: '#EF4444',
    unknown: '#8BA0BA',
  }[systemHealth];

  const healthLabel = {
    healthy: 'OPERATIONAL',
    degraded: 'DEGRADED',
    critical: 'CRITICAL',
    unknown: 'CONNECTING…',
  }[systemHealth];

  const activeFailed = snapshot ? Object.values(snapshot.masks).filter(Boolean).length : 0;
  const activeRecon = snapshot ? Object.keys(snapshot.reconstructions).length : 0;
  const rmse = metrics?.rmse ?? 0;
  const fcr = metrics?.fcr ?? 0;

  return (
    <header
      className="flex items-center justify-between px-6 py-2.5 border-b border-[#2A3545] shrink-0 relative z-20 shadow-[0_4px_20px_rgba(0,0,0,0.15)]"
      style={{ background: 'var(--premium-card-bg)' }}
    >
      {/* Brand */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-3">
          <div className="w-7 h-7 rounded-sm bg-[#3B82F6] flex items-center justify-center">
            <svg viewBox="0 0 16 16" className="w-4 h-4 fill-white" aria-hidden="true">
              <circle cx="8" cy="8" r="2.5" />
              <circle cx="3" cy="5" r="1.5" />
              <circle cx="13" cy="5" r="1.5" />
              <circle cx="3" cy="11" r="1.5" />
              <circle cx="13" cy="11" r="1.5" />
              <line x1="8" y1="8" x2="3" y2="5" stroke="white" strokeWidth="0.8" />
              <line x1="8" y1="8" x2="13" y2="5" stroke="white" strokeWidth="0.8" />
              <line x1="8" y1="8" x2="3" y2="11" stroke="white" strokeWidth="0.8" />
              <line x1="8" y1="8" x2="13" y2="11" stroke="white" strokeWidth="0.8" />
            </svg>
          </div>
          <div>
            <h1 className="text-sm font-semibold tracking-wider text-[#E8EDF4]">TraffiTwin AI</h1>
            <p className="text-[10px] text-[#8BA0BA] tracking-widest">SMART CITY OPERATIONS CENTER</p>
          </div>
        </div>
        <button
          onClick={() => openBriefing()}
          className="px-2.5 py-1 rounded-full border text-[8px] font-mono tracking-widest transition-all duration-150 cursor-pointer text-[#8BA0BA] border-[#2A3545] bg-[#121820]/45 hover:text-white hover:border-[#F59E0B]/50 hover:bg-[#F59E0B]/10"
        >
          MISSION
        </button>
      </div>

      {/* Center: main metrics inside a centered pill */}
      <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 flex items-center gap-5 px-6 py-1.5 rounded-full border border-[#2A3545] bg-[#121820]/55 backdrop-blur-md shadow-[0_4px_15px_rgba(0,0,0,0.3)]">
        <StatPill
          label="ACTIVE FAILURES"
          value={activeFailed}
          color={activeFailed > 0 ? '#EF4444' : '#10B981'}
          dot
        />
        <StatPill
          label="AI RECONSTRUCTED"
          value={activeRecon}
          color={activeRecon > 0 ? '#8B5CF6' : '#8BA0BA'}
          dot
        />
        <StatPill
          label="RECON ACC"
          value={metrics ? `${fcr.toFixed(1)}%` : '—'}
          color={metrics ? (fcr >= 95 ? '#10B981' : fcr >= 80 ? '#F59E0B' : '#EF4444') : '#8BA0BA'}
        />
        <StatPill
          label="RMSE"
          value={rmse > 0 ? `${rmse.toFixed(2)} mph` : '—'}
          color="#8BA0BA"
        />
      </div>

      {/* Right: Operational Status */}
      <div className="flex items-center gap-2" role="status" aria-label={`System health: ${healthLabel}`}>
        <AnimatePresence mode="wait">
          <motion.div
            key={systemHealth}
            className="w-2.5 h-2.5 rounded-full"
            style={{ background: healthColor }}
            initial={{ scale: 0.5, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.5, opacity: 0 }}
            transition={{ duration: 0.2 }}
          />
        </AnimatePresence>
        <span className="text-xs font-mono font-semibold tracking-widest" style={{ color: healthColor }}>
          {healthLabel}
        </span>
      </div>
    </header>
  );
}
