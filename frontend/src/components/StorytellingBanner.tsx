import { motion, AnimatePresence } from 'motion/react';
import { useTwinStore } from '../store/twinStore';

const BANNER_STYLES = {
  fault: {
    bg: 'bg-[#EF4444]/15',
    border: 'border-[#EF4444]/50',
    text: 'text-[#EF4444]',
    icon: '⚠',
  },
  ai: {
    bg: 'bg-[#8B5CF6]/15',
    border: 'border-[#8B5CF6]/50',
    text: 'text-[#8B5CF6]',
    icon: '✦',
  },
  recovery: {
    bg: 'bg-[#10B981]/15',
    border: 'border-[#10B981]/50',
    text: 'text-[#10B981]',
    icon: '✓',
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
          initial={{ opacity: 0, y: -12 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -8 }}
          transition={{ duration: 0.22, ease: 'easeOut' }}
          className={`absolute top-3 left-1/2 -translate-x-1/2 z-40 flex items-center gap-3 px-5 py-3 rounded border backdrop-blur-sm shadow-lg cursor-pointer select-none ${BANNER_STYLES[banner.type].bg} ${BANNER_STYLES[banner.type].border}`}
          onClick={dismiss}
          role="alert"
          aria-live="assertive"
        >
          <span className={`text-lg ${BANNER_STYLES[banner.type].text}`}>
            {BANNER_STYLES[banner.type].icon}
          </span>
          <span className={`text-sm font-mono font-bold tracking-widest ${BANNER_STYLES[banner.type].text}`}>
            {banner.message}
          </span>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
