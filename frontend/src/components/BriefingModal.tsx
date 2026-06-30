import { useEffect, useState, useRef } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { useTwinStore } from '../store/twinStore';

export function BriefingModal() {
  const isBriefingOpen = useTwinStore((s) => s.isBriefingOpen);
  const closeBriefing = useTwinStore((s) => s.closeBriefing);
  const [countdown, setCountdown] = useState(6);
  const timerRef = useRef<any>(null);

  // Reset countdown and start timer whenever modal opens
  useEffect(() => {
    if (isBriefingOpen) {
      setCountdown(6);
      
      if (timerRef.current) clearInterval(timerRef.current);
      
      timerRef.current = setInterval(() => {
        setCountdown((prev) => {
          if (prev <= 1) {
            if (timerRef.current) clearInterval(timerRef.current);
            closeBriefing();
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    }

    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [isBriefingOpen, closeBriefing]);

  // Escape key listener to close modal
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isBriefingOpen) {
        closeBriefing();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isBriefingOpen, closeBriefing]);

  return (
    <AnimatePresence>
      {isBriefingOpen && (
        <>
          {/* Backdrop overlay with blur */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={closeBriefing}
            className="fixed inset-0 bg-black/75 backdrop-blur-[6px] z-50 cursor-pointer"
            aria-hidden="true"
          />

          {/* Modal Container */}
          <div className="fixed inset-0 flex items-center justify-center z-50 pointer-events-none p-4">
            <motion.div
              initial={{ opacity: 0, scale: 0.94, y: 10 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.94, y: 10 }}
              transition={{ type: 'spring', stiffness: 350, damping: 28 }}
              className="relative w-full max-w-[520px] rounded-xl p-6 pointer-events-auto overflow-hidden"
              style={{
                background: 'linear-gradient(180deg, rgba(26,34,48,0.98), rgba(18,24,32,0.98))',
                border: '1px solid rgba(245, 158, 11, 0.25)', // thin amber border
                boxShadow: '0 20px 40px rgba(0,0,0,0.5), 0 0 20px rgba(245, 158, 11, 0.05)',
              }}
              role="dialog"
              aria-modal="true"
              aria-labelledby="briefing-title"
            >
              {/* Top Accent Line */}
              <div className="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-transparent via-[#F59E0B]/60 to-transparent" />

              {/* Close Button */}
              <button
                onClick={closeBriefing}
                className="absolute top-4 right-4 w-6 h-6 rounded-full flex items-center justify-center border border-[#2A3545] bg-[#121820]/40 text-[#8BA0BA] hover:text-white hover:border-amber-500/50 transition-all duration-150 cursor-pointer text-xs font-mono"
                aria-label="Dismiss briefing"
              >
                ✕
              </button>

              {/* Header Title */}
              <div className="mb-4">
                <p className="text-[9px] font-mono text-amber-500 tracking-[0.2em] font-bold">
                  MISSION PROTOCOL
                </p>
                <h2
                  id="briefing-title"
                  className="text-base font-mono font-bold tracking-widest text-[#E8EDF4] mt-1"
                >
                  ABOUT TRAFFITWIN AI
                </h2>
              </div>

              {/* Body Content */}
              <div className="space-y-4 text-xs leading-relaxed text-[#C8D8E8] font-mono">
                <p>
                  TraffiTwin AI is a self-healing traffic digital twin that restores situational awareness during sensor failures.
                </p>
                <p>
                  When traffic sensors go offline, the system reconstructs missing traffic states using graph-based AI, preserving network observability and preventing operational blind spots.
                </p>
                
                {/* Key Points */}
                <div
                  className="p-3.5 rounded-lg space-y-2 border border-[#2A3545] bg-[#0B0F14]/40"
                >
                  <p className="text-[9px] font-mono text-[#8BA0BA] tracking-wider uppercase mb-1">
                    System Capabilities
                  </p>
                  <div className="flex items-start gap-2.5">
                    <span className="text-amber-500 select-none">•</span>
                    <span>Detects sensor outages in real time</span>
                  </div>
                  <div className="flex items-start gap-2.5">
                    <span className="text-amber-500 select-none">•</span>
                    <span>Reconstructs missing traffic conditions using graph-based AI</span>
                  </div>
                  <div className="flex items-start gap-2.5">
                    <span className="text-amber-500 select-none">•</span>
                    <span>Maintains &gt;97% network observability during failures</span>
                  </div>
                </div>
              </div>

              {/* Footer with countdown */}
              <div className="mt-6 pt-4 border-t border-[#2A3545] flex items-center justify-between">
                <div className="flex items-center gap-1.5 text-[9px] font-mono text-[#8BA0BA] tracking-wider">
                  <span>CLOSING IN</span>
                  <div className="inline-flex items-center justify-center min-w-[14px]">
                    <AnimatePresence mode="popLayout">
                      <motion.span
                        key={countdown}
                        initial={{ opacity: 0, y: -6 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: 6 }}
                        transition={{ duration: 0.15 }}
                        className="font-bold text-amber-500"
                      >
                        {countdown}
                      </motion.span>
                    </AnimatePresence>
                  </div>
                  <span>SEC</span>
                </div>
                
                <button
                  onClick={closeBriefing}
                  className="px-4 py-1.5 rounded-full border text-[10px] font-mono tracking-widest transition-all duration-150 cursor-pointer text-white border-amber-500/30 bg-amber-500/10 hover:border-amber-500 hover:bg-amber-500/25"
                >
                  ENTER TERMINAL
                </button>
              </div>
            </motion.div>
          </div>
        </>
      )}
    </AnimatePresence>
  );
}
