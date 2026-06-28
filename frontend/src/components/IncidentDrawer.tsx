import { motion, AnimatePresence } from 'motion/react';
import { useTwinStore } from '../store/twinStore';
import type { GraphLayoutNode } from '../types/api';

interface Props {
  layout: GraphLayoutNode[];
}

export function IncidentDrawer({ layout }: Props) {
  const selectedId = useTwinStore((s) => s.selectedSensorId);
  const snapshot = useTwinStore((s) => s.snapshot);
  const setSelectedSensor = useTwinStore((s) => s.setSelectedSensor);

  const node = layout.find((n) => n.id === selectedId);

  const id = selectedId != null ? String(selectedId) : null;
  const isFailed = id != null && snapshot?.masks[id] === true;
  const isReconstructed = id != null && id in (snapshot?.reconstructions ?? {});
  const speed = id != null ? (snapshot?.readings[id] ?? null) : null;
  const aiSpeed = id != null ? (snapshot?.reconstructions[id] ?? null) : null;

  // Count neighbors (nodes connected to this one — approximate via proximity)
  const neighborCount = layout.filter((n) => {
    if (!node || n.id === selectedId) return false;
    const dx = n.x - node.x;
    const dy = n.y - node.y;
    return Math.sqrt(dx * dx + dy * dy) < 0.15;
  }).length;

  const status = isFailed ? (isReconstructed ? 'RECONSTRUCTED' : 'FAILED') : 'HEALTHY';
  const statusColor = isFailed ? (isReconstructed ? '#8B5CF6' : '#EF4444') : '#10B981';

  return (
    <AnimatePresence>
      {selectedId != null && (
        <motion.aside
          initial={{ x: '100%', opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          exit={{ x: '100%', opacity: 0 }}
          transition={{ duration: 0.25, ease: 'easeOut' }}
          className="fixed top-0 right-0 h-full w-72 bg-[#121820] border-l border-[#2A3545] shadow-2xl z-30 flex flex-col"
          role="dialog"
          aria-label={`Incident details for Sensor ${selectedId}`}
          aria-modal="false"
        >
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-4 border-b border-[#2A3545]">
            <div>
              <p className="text-[10px] font-mono text-[#8BA0BA] tracking-widest">INCIDENT DETAILS</p>
              <h2 className="text-lg font-mono font-bold text-[#E8EDF4] mt-0.5">Sensor {selectedId}</h2>
            </div>
            <button
              onClick={() => setSelectedSensor(null)}
              className="w-7 h-7 flex items-center justify-center rounded hover:bg-[#1A2230] text-[#8BA0BA] hover:text-[#E8EDF4] transition-colors text-sm"
              aria-label="Close incident drawer"
            >
              ✕
            </button>
          </div>

          {/* Status badge */}
          <div className="px-4 py-3 border-b border-[#2A3545]">
            <div
              className="flex items-center gap-2 px-3 py-2 rounded text-sm font-mono font-bold"
              style={{ backgroundColor: statusColor + '20', color: statusColor, border: `1px solid ${statusColor}40` }}
            >
              <span>{isFailed ? (isReconstructed ? '✦' : '⚠') : '✓'}</span>
              <span>{status}</span>
            </div>
          </div>

          {/* Details */}
          <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-3">
            <DrawerRow label="Sensor ID" value={String(selectedId)} />
            <DrawerRow label="Current Status" value={status} color={statusColor} />
            {speed != null && (
              <DrawerRow label="Last Known Speed" value={`${speed.toFixed(1)} mph`} />
            )}
            {aiSpeed != null && (
              <DrawerRow label="AI Estimated Speed" value={`${aiSpeed.toFixed(1)} mph`} color="#8B5CF6" />
            )}
            {speed != null && aiSpeed != null && (
              <DrawerRow
                label="Estimation Error"
                value={`${Math.abs(speed - aiSpeed).toFixed(1)} mph`}
                color={Math.abs(speed - aiSpeed) < 5 ? '#10B981' : '#F59E0B'}
              />
            )}
            <DrawerRow label="Nearby Sensors" value={String(neighborCount)} />
            <DrawerRow
              label="Recovery Status"
              value={isReconstructed ? 'AI Reconstructed' : isFailed ? 'Awaiting Reconstruction' : 'In Service'}
              color={isReconstructed ? '#8B5CF6' : isFailed ? '#EF4444' : '#10B981'}
            />
            {isReconstructed && (
              <DrawerRow label="Confidence" value="High (FCR 97.03%)" color="#10B981" />
            )}
            {node && (
              <>
                <DrawerRow label="Network Position X" value={node.x.toFixed(4)} />
                <DrawerRow label="Network Position Y" value={node.y.toFixed(4)} />
              </>
            )}
          </div>

          {/* Footer */}
          <div className="px-4 py-3 border-t border-[#2A3545]">
            <p className="text-[10px] font-mono text-[#2A3545]">
              METR-LA sensor network · Los Angeles, CA
            </p>
          </div>
        </motion.aside>
      )}
    </AnimatePresence>
  );
}

function DrawerRow({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div className="flex items-center justify-between py-1.5 border-b border-[#2A3545]/50">
      <span className="text-[11px] font-mono text-[#8BA0BA]">{label}</span>
      <span className="text-[11px] font-mono font-semibold" style={{ color: color ?? '#E8EDF4' }}>
        {value}
      </span>
    </div>
  );
}
