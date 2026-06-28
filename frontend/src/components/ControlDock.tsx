import { useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { useTwinStore } from '../store/twinStore';
import { api } from '../api/trafitwin';

interface Props {
  onStep: () => void;
}

export function ControlDock({ onStep }: Props) {
  const isAutoplay = useTwinStore((s) => s.isAutoplay);
  const toggleAutoplay = useTwinStore((s) => s.toggleAutoplay);
  const clearEvents = useTwinStore((s) => s.clearEvents);
  const addEvent = useTwinStore((s) => s.addEvent);

  const [stepping, setStepping] = useState(false);
  const [showInjectModal, setShowInjectModal] = useState(false);

  async function handleStep() {
    if (stepping) return;
    setStepping(true);
    try {
      await api.stepSimulation(1);
      onStep();
    } finally {
      setStepping(false);
    }
  }

  return (
    <>
      <div
        className="flex items-center justify-between px-6 py-3 border-t border-[#2A3545] bg-[#0B0F14] shrink-0"
        role="toolbar"
        aria-label="Simulation controls"
      >
        <div className="flex items-center gap-3">
          {/* Step */}
          <button
            onClick={handleStep}
            disabled={stepping || isAutoplay}
            className="flex items-center gap-2 px-4 py-2 rounded bg-[#1A2230] border border-[#2A3545] text-xs font-mono text-[#E8EDF4] hover:border-[#3B82F6] hover:text-[#3B82F6] disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            aria-label="Step simulation by one time step"
          >
            {stepping ? (
              <span className="w-3 h-3 border border-[#3B82F6] border-t-transparent rounded-full animate-spin" />
            ) : (
              <span>▶</span>
            )}
            STEP
          </button>

          {/* Auto Play */}
          <button
            onClick={toggleAutoplay}
            className={`flex items-center gap-2 px-4 py-2 rounded border text-xs font-mono transition-colors ${
              isAutoplay
                ? 'bg-[#3B82F6]/20 border-[#3B82F6] text-[#3B82F6]'
                : 'bg-[#1A2230] border-[#2A3545] text-[#E8EDF4] hover:border-[#3B82F6] hover:text-[#3B82F6]'
            }`}
            aria-pressed={isAutoplay}
            aria-label={isAutoplay ? 'Stop auto play' : 'Start auto play'}
          >
            <span>{isAutoplay ? '⏸' : '⏵'}</span>
            {isAutoplay ? 'PAUSE' : 'AUTO PLAY'}
          </button>

          {/* Inject Failure */}
          <button
            onClick={() => setShowInjectModal(true)}
            className="flex items-center gap-2 px-4 py-2 rounded bg-[#F59E0B]/10 border border-[#F59E0B]/40 text-[#F59E0B] text-xs font-mono hover:bg-[#F59E0B]/20 hover:border-[#F59E0B] transition-colors"
            aria-label="Inject sensor failure"
          >
            <span>⚡</span>
            INJECT FAILURE
          </button>
        </div>

        <div className="flex items-center gap-3">
          {/* Clear timeline */}
          <button
            onClick={clearEvents}
            className="px-3 py-2 rounded bg-[#1A2230] border border-[#2A3545] text-[#8BA0BA] text-xs font-mono hover:text-[#E8EDF4] transition-colors"
            aria-label="Clear event timeline"
          >
            CLEAR LOG
          </button>

          {/* Benchmark info badge */}
          <div className="hidden lg:flex items-center gap-3 border-l border-[#2A3545] pl-4 text-[11px] font-mono text-[#8BA0BA]">
            <span>METR-LA · 207 sensors · 5-min intervals</span>
            <span className="text-[#2A3545]">|</span>
            <span className="text-[#10B981]">LightGBM STGBM · MAE 2.51 · FCR 97.03%</span>
          </div>
        </div>
      </div>

      {/* Inject Failure Modal */}
      <AnimatePresence>
        {showInjectModal && (
          <InjectFailureModal
            onClose={() => setShowInjectModal(false)}
            onInject={async (id, dur) => {
              await api.injectFailure(id, dur);
              addEvent({
                severity: 'FAULT',
                message: `Manual failure injected on Sensor ${id} for ${dur} steps`,
                sensor_id: id,
              });
              setShowInjectModal(false);
              onStep();
            }}
          />
        )}
      </AnimatePresence>
    </>
  );
}

function InjectFailureModal({ onClose, onInject }: { onClose: () => void; onInject: (id: number, dur: number) => Promise<void> }) {
  const [sensorId, setSensorId] = useState('50');
  const [duration, setDuration] = useState('5');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const id = parseInt(sensorId);
    const dur = parseInt(duration);
    if (isNaN(id) || id < 0 || id > 206) { setError('Sensor ID must be 0–206'); return; }
    if (isNaN(dur) || dur < 1 || dur > 30) { setError('Duration must be 1–30 steps'); return; }
    setLoading(true);
    try {
      await onInject(id, dur);
    } catch (err) {
      setError('Failed to inject failure. Is the backend running?');
    } finally {
      setLoading(false);
    }
  }

  return (
    <motion.div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      onClick={onClose}
    >
      <motion.div
        className="bg-[#1A2230] border border-[#F59E0B]/40 rounded-lg shadow-2xl p-6 w-80"
        initial={{ scale: 0.92, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.92, opacity: 0 }}
        transition={{ duration: 0.18 }}
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-labelledby="inject-title"
        aria-modal="true"
      >
        <div className="flex items-center gap-2 mb-4">
          <span className="text-[#F59E0B]">⚡</span>
          <h2 id="inject-title" className="text-sm font-mono font-semibold text-[#E8EDF4]">
            INJECT SENSOR FAILURE
          </h2>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div>
            <label className="block text-[10px] font-mono text-[#8BA0BA] tracking-widest mb-1">
              SENSOR ID (0 – 206)
            </label>
            <input
              type="number"
              min={0}
              max={206}
              value={sensorId}
              onChange={(e) => setSensorId(e.target.value)}
              className="w-full bg-[#121820] border border-[#2A3545] rounded px-3 py-2 text-sm font-mono text-[#E8EDF4] focus:border-[#F59E0B] outline-none transition-colors"
              autoFocus
            />
          </div>

          <div>
            <label className="block text-[10px] font-mono text-[#8BA0BA] tracking-widest mb-1">
              DURATION (steps)
            </label>
            <input
              type="number"
              min={1}
              max={30}
              value={duration}
              onChange={(e) => setDuration(e.target.value)}
              className="w-full bg-[#121820] border border-[#2A3545] rounded px-3 py-2 text-sm font-mono text-[#E8EDF4] focus:border-[#F59E0B] outline-none transition-colors"
            />
          </div>

          {error && (
            <p className="text-[#EF4444] text-xs font-mono">{error}</p>
          )}

          <div className="flex gap-2 pt-1">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 py-2 rounded bg-[#121820] border border-[#2A3545] text-xs font-mono text-[#8BA0BA] hover:text-[#E8EDF4] transition-colors"
            >
              CANCEL
            </button>
            <button
              type="submit"
              disabled={loading}
              className="flex-1 py-2 rounded bg-[#F59E0B]/20 border border-[#F59E0B] text-[#F59E0B] text-xs font-mono font-semibold hover:bg-[#F59E0B]/30 disabled:opacity-50 transition-colors"
            >
              {loading ? 'INJECTING…' : 'INJECT'}
            </button>
          </div>
        </form>
      </motion.div>
    </motion.div>
  );
}
