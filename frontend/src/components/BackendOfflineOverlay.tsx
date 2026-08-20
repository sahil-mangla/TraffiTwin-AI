import { motion } from 'motion/react';
import { useTwinStore } from '../store/twinStore';
import { useEffect, useState } from 'react';

export function BackendOfflineOverlay() {
  const isOffline = useTwinStore((s) => s.isBackendOffline);
  const wakeUpStatus = useTwinStore((s) => s.wakeUpStatus);
  const wakeUpRetries = useTwinStore((s) => s.wakeUpRetries);
  const [dots, setDots] = useState('');

  useEffect(() => {
    if (!isOffline) return;
    const t = setInterval(() => setDots((d) => (d.length >= 3 ? '' : d + '.')), 500);
    return () => clearInterval(t);
  }, [isOffline]);

  if (!isOffline) return null;

  // ── Differentiated states ──────────────────────────────────────────────────
  const isWaking = wakeUpStatus === 'waking';
  const isFailed = wakeUpStatus === 'failed';

  const icon = isFailed ? '✕' : isWaking ? '⏳' : '↻';
  const iconColor = isFailed ? '#EF4444' : isWaking ? '#F59E0B' : '#EF4444';
  const borderColor = isFailed
    ? 'border-[#EF4444]/40'
    : isWaking
    ? 'border-[#F59E0B]/40'
    : 'border-[#EF4444]/40';

  const title = isFailed
    ? 'BACKEND UNREACHABLE'
    : isWaking
    ? 'STARTING BACKEND'
    : 'BACKEND OFFLINE';

  const subtitle = isFailed
    ? `Failed after ${wakeUpRetries} retries — try refreshing the page`
    : isWaking
    ? `Waking up HF Space${wakeUpRetries > 0 ? ` (attempt ${wakeUpRetries}/10)` : ''}${dots}`
    : `Attempting to reconnect${dots}`;

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-[#0B0F14]/95 backdrop-blur-sm"
      role="alert"
      aria-live="assertive"
    >
      <div className="text-center max-w-sm">
        <div
          className={`w-16 h-16 rounded-full border-2 ${borderColor} flex items-center justify-center mx-auto mb-6`}
        >
          <span style={{ color: iconColor }} className="text-2xl">
            {icon}
          </span>
        </div>
        <h2
          className="text-xl font-mono font-bold tracking-widest mb-2"
          style={{ color: iconColor }}
        >
          {title}
        </h2>
        <p
          className="text-sm font-mono text-[#8BA0BA] mb-6"
          aria-live="polite"
          aria-atomic="true"
        >
          {subtitle}
        </p>
        {isWaking && (
          <p className="text-xs font-mono text-[#2A3545] mb-2">
            Hugging Face free-tier Spaces sleep after inactivity.
            <br />
            Cold-start takes ~30–90 seconds.
          </p>
        )}
        <div className="text-xs font-mono text-[#2A3545]">
          Target: {import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}
        </div>
        {!import.meta.env.VITE_API_BASE_URL && (
          <div className="mt-3 text-[11px] font-mono text-[#2A3545]">
            uvicorn backend.api.app:app --port 8000
          </div>
        )}
      </div>
    </motion.div>
  );
}
