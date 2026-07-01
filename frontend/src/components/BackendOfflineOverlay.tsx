import { motion } from 'motion/react';
import { useTwinStore } from '../store/twinStore';
import { useEffect, useState } from 'react';

export function BackendOfflineOverlay() {
  const isOffline = useTwinStore((s) => s.isBackendOffline);
  const [dots, setDots] = useState('');

  useEffect(() => {
    if (!isOffline) return;
    const t = setInterval(() => setDots((d) => (d.length >= 3 ? '' : d + '.')), 500);
    return () => clearInterval(t);
  }, [isOffline]);

  if (!isOffline) return null;

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-[#0B0F14]/95 backdrop-blur-sm"
      role="alert"
      aria-live="assertive"
    >
      <div className="text-center">
        <div className="w-16 h-16 rounded-full border-2 border-[#EF4444]/40 flex items-center justify-center mx-auto mb-6">
          <span className="text-[#EF4444] text-2xl">⚠</span>
        </div>
        <h2 className="text-xl font-mono font-bold text-[#EF4444] tracking-widest mb-2">
          BACKEND OFFLINE
        </h2>
        <p className="text-sm font-mono text-[#8BA0BA] mb-6">
          Attempting to reconnect{dots}
        </p>
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
