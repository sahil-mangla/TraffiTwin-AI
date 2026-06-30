import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { useTwinStore } from '../store/twinStore';

function formatAge(date: Date | null): string {
  if (!date) return '—';
  const secs = Math.floor((Date.now() - date.getTime()) / 1000);
  if (secs < 5) return 'just now';
  if (secs < 60) return `${secs}s ago`;
  return `${Math.floor(secs / 60)}m ago`;
}

export function Header() {
  const systemHealth = useTwinStore((s) => s.systemHealth);
  const isAutoplay = useTwinStore((s) => s.isAutoplay);
  const lastUpdated = useTwinStore((s) => s.lastUpdated);
  const [now, setNow] = useState(new Date());
  const [age, setAge] = useState('—');

  useEffect(() => {
    const t = setInterval(() => {
      setNow(new Date());
      setAge(formatAge(lastUpdated));
    }, 1000);
    return () => clearInterval(t);
  }, [lastUpdated]);

  const healthColor = {
    healthy: 'text-[#10B981]',
    degraded: 'text-[#F59E0B]',
    critical: 'text-[#EF4444]',
    unknown: 'text-[#8BA0BA]',
  }[systemHealth];

  const healthLabel = {
    healthy: 'OPERATIONAL',
    degraded: 'DEGRADED',
    critical: 'CRITICAL',
    unknown: 'CONNECTING…',
  }[systemHealth];

  return (
    <header className="flex items-center justify-between px-6 py-3 border-b border-[#2A3545] shrink-0 relative z-20 shadow-[0_4px_20px_rgba(0,0,0,0.15)]" style={{ background: 'var(--premium-card-bg)' }}>
      {/* Brand */}
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

      {/* Center: status indicators */}
      <div className="flex items-center gap-8">
        {/* System health */}
        <div className="flex items-center gap-2" role="status" aria-label={`System health: ${healthLabel}`}>
          <AnimatePresence mode="wait">
            <motion.div
              key={systemHealth}
              className={`w-2 h-2 rounded-full ${
                systemHealth === 'healthy' ? 'bg-[#10B981]' :
                systemHealth === 'degraded' ? 'bg-[#F59E0B]' :
                systemHealth === 'critical' ? 'bg-[#EF4444]' : 'bg-[#8BA0BA]'
              }`}
              initial={{ scale: 0.5, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.5, opacity: 0 }}
              transition={{ duration: 0.2 }}
            />
          </AnimatePresence>
          <span className={`text-xs font-mono font-semibold tracking-widest ${healthColor}`}>
            {healthLabel}
          </span>
        </div>

        {/* Sim state */}
        <div className="flex items-center gap-2">
          <div className={`w-1.5 h-1.5 rounded-full ${isAutoplay ? 'bg-[#3B82F6] animate-pulse' : 'bg-[#2A3545]'}`} />
          <span className="text-[11px] font-mono text-[#8BA0BA] tracking-widest">
            {isAutoplay ? 'AUTO PLAY' : 'STANDBY'}
          </span>
        </div>
      </div>

      {/* Right: time */}
      <div className="text-right">
        <div className="text-xs font-mono text-[#E8EDF4]">
          {now.toLocaleTimeString('en-US', { hour12: false })}
        </div>
        <div className="text-[10px] font-mono text-[#8BA0BA]">Updated {age}</div>
      </div>
    </header>
  );
}
