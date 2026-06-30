import { motion, AnimatePresence } from 'motion/react';
import { useTwinStore } from '../store/twinStore';

const BANNER_STYLES = {
  fault: {
    bg: 'bg-[#EF4444]/20',
    border: 'border-[#EF4444]/40',
    text: 'text-[#EF4444]',
    icon: '⚠',
    bar: 'bg-[#EF4444]',
    duration: 2000,
  },
  ai: {
    bg: 'bg-[#8B5CF6]/20',
    border: 'border-[#8B5CF6]/40',
    text: 'text-[#8B5CF6]',
    icon: '✦',
    bar: 'bg-[#8B5CF6]',
    duration: 0,
  },
  recovery: {
    bg: 'bg-[#10B981]/20',
    border: 'border-[#10B981]/40',
    text: 'text-[#10B981]',
    icon: '✓',
    bar: 'bg-[#10B981]',
    duration: 4000,
  },
};

export function StorytellingBanner() {
  const banner = useTwinStore((s) => s.activeBanner);
  const dismiss = useTwinStore((s) => s.dismissBanner);

  return (
    <AnimatePresence mode="wait">
      {banner && (
        <motion.div
          key={banner.type + banner.message}
          initial={{ opacity: 0, y: -20, scale: 0.95 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: -15, scale: 0.95 }}
          transition={{ type: "spring", stiffness: 400, damping: 25 }}
          className={`absolute top-4 left-1/2 -translate-x-1/2 z-40 overflow-hidden rounded-lg border backdrop-blur-md shadow-2xl cursor-pointer select-none ${BANNER_STYLES[banner.type].bg} ${BANNER_STYLES[banner.type].border}`}
          onClick={dismiss}
          role="alert"
          aria-live="assertive"
        >
          <div className="flex items-center gap-4 px-6 py-4">
            <span className={`text-2xl ${BANNER_STYLES[banner.type].text}`}>
              {BANNER_STYLES[banner.type].icon}
            </span>
            <div className="flex flex-col">
              <span className={`text-sm font-mono font-bold tracking-widest ${BANNER_STYLES[banner.type].text}`}>
                {banner.message}
              </span>
              {banner.subtitle && (
                <span className="text-xs font-mono text-[#E8EDF4] mt-0.5">
                  {banner.subtitle}
                </span>
              )}
            </div>
          </div>
          
          {BANNER_STYLES[banner.type].duration > 0 && (
            <motion.div 
              className={`h-[2px] ${BANNER_STYLES[banner.type].bar} w-full origin-left`}
              initial={{ scaleX: 1 }}
              animate={{ scaleX: 0 }}
              transition={{ duration: BANNER_STYLES[banner.type].duration / 1000, ease: "linear" }}
            />
          )}
        </motion.div>
      )}
    </AnimatePresence>
  );
}
