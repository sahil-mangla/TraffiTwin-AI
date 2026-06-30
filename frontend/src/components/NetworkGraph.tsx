import { useEffect, useRef, useState, useCallback } from 'react';
import { useTwinStore } from '../store/twinStore';
import type { GraphLayoutNode, SensorInfo, NodeStatus, GraphEdge } from '../types/api';

interface Props {
  layout: GraphLayoutNode[];
  edges?: GraphEdge[];
}

const NODE_R = 4;
const FAIL_R = 10;
const RECON_R = 6;

const COLORS: Record<NodeStatus, string> = {
  healthy: '#10B981',
  failed: '#EF4444',
  reconstructed: '#8B5CF6',
};

function getSensorStatus(
  id: string,
  masks: Record<string, boolean>,
  reconstructions: Record<string, number>
): NodeStatus {
  if (masks[id]) {
    if (id in reconstructions) return 'reconstructed';
    return 'failed';
  }
  return 'healthy';
}

function drawCross(ctx: CanvasRenderingContext2D, cx: number, cy: number, r: number) {
  const s = r * 0.5;
  ctx.beginPath();
  ctx.moveTo(cx - s, cy - s); ctx.lineTo(cx + s, cy + s);
  ctx.moveTo(cx + s, cy - s); ctx.lineTo(cx - s, cy + s);
  ctx.stroke();
}

function drawCheck(ctx: CanvasRenderingContext2D, cx: number, cy: number, r: number) {
  const s = r * 0.4;
  ctx.beginPath();
  ctx.moveTo(cx - s, cy);
  ctx.lineTo(cx - s * 0.2, cy + s * 0.7);
  ctx.lineTo(cx + s, cy - s * 0.5);
  ctx.stroke();
}

export function NetworkGraph({ layout, edges = [] }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const wrapRef = useRef<HTMLDivElement>(null);
  const animRef = useRef<number>(0);
  const flashRef = useRef<Map<string, { until: number; color: string }>>(new Map());

  const snapshot = useTwinStore((s) => s.snapshot);
  const setSelectedSensor = useTwinStore((s) => s.setSelectedSensor);
  const [tooltip, setTooltip] = useState<{ x: number; y: number; sensor: SensorInfo } | null>(null);

  // Keep latest snapshot in a ref so the RAF loop sees current data
  const snapshotRef = useRef(snapshot);
  snapshotRef.current = snapshot;

  // Track previous masks to detect transitions for flash effects
  const prevMasksRef = useRef<Record<string, boolean>>({});

  // Map id → canvas coords (cached on resize)
  const coordsRef = useRef<Map<number, { cx: number; cy: number }>>(new Map());

  function computeCoords(W: number, H: number) {
    const map = new Map<number, { cx: number; cy: number }>();
    for (const node of layout) {
      map.set(node.id, { cx: node.x * W, cy: node.y * H });
    }
    coordsRef.current = map;
  }

  // Resize observer
  useEffect(() => {
    if (!wrapRef.current || !canvasRef.current) return;
    const ro = new ResizeObserver((entries) => {
      for (const e of entries) {
        const { width, height } = e.contentRect;
        canvasRef.current!.width = width * devicePixelRatio;
        canvasRef.current!.height = height * devicePixelRatio;
        canvasRef.current!.style.width = `${width}px`;
        canvasRef.current!.style.height = `${height}px`;
        computeCoords(width * devicePixelRatio, height * devicePixelRatio);
      }
    });
    ro.observe(wrapRef.current);
    return () => ro.disconnect();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [layout]);

  // Detect transitions and trigger flashes
  useEffect(() => {
    if (!snapshot) return;
    const prev = prevMasksRef.current;
    for (const [id, failed] of Object.entries(snapshot.masks)) {
      const wasFailed = prev[id] === true;
      if (failed && !wasFailed) {
        // New fault flash
        flashRef.current.set(id, { until: Date.now() + 600, color: '#EF4444' });
      }
      if (!failed && wasFailed) {
        // Recovery flash
        flashRef.current.set(id, { until: Date.now() + 800, color: '#8B5CF6' });
      }
    }
    prevMasksRef.current = { ...snapshot.masks };
  }, [snapshot]);

  // Draw loop
  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const W = canvas.width;
    const H = canvas.height;
    const snap = snapshotRef.current;
    const now = Date.now();

    ctx.clearRect(0, 0, W, H);

    // Draw edges
    ctx.lineWidth = 0.5;
    for (const edge of edges) {
      const src = coordsRef.current.get(edge.source);
      const tgt = coordsRef.current.get(edge.target);
      if (src && tgt) {
        ctx.strokeStyle = `rgba(139, 160, 186, ${Math.min(0.6, edge.weight * 0.4)})`;
        ctx.beginPath();
        ctx.moveTo(src.cx, src.cy);
        ctx.lineTo(tgt.cx, tgt.cy);
        ctx.stroke();
      }
    }

    for (const node of layout) {
      const coord = coordsRef.current.get(node.id);
      if (!coord) continue;
      const { cx, cy } = coord;
      const id = String(node.id);
      const status: NodeStatus = snap
        ? getSensorStatus(id, snap.masks, snap.reconstructions)
        : 'healthy';

      const color = COLORS[status];
      const r = status === 'failed' ? FAIL_R : status === 'reconstructed' ? RECON_R : NODE_R;

      // Flash overlay
      const flash = flashRef.current.get(id);
      if (flash && now < flash.until) {
        ctx.beginPath();
        ctx.arc(cx, cy, r * 2.5, 0, Math.PI * 2);
        ctx.fillStyle = flash.color + '33';
        ctx.fill();
      } else if (flash && now >= flash.until) {
        flashRef.current.delete(id);
      }

      // Pulse ring for failed nodes
      if (status === 'failed') {
        const phase = ((now % 1500) / 1500);
        const pulseR = r + phase * r * 3;
        const alpha = Math.max(0, 0.6 - phase * 0.8);
        ctx.beginPath();
        ctx.arc(cx, cy, pulseR, 0, Math.PI * 2);
        ctx.strokeStyle = `rgba(239,68,68,${alpha})`;
        ctx.lineWidth = 1.5;
        ctx.stroke();
        
        ctx.beginPath();
        ctx.arc(cx, cy, r + 2, 0, Math.PI * 2);
        ctx.strokeStyle = 'rgba(239,68,68,0.8)';
        ctx.lineWidth = 1.5;
        ctx.stroke();
      }

      // Node body
      ctx.beginPath();
      ctx.arc(cx, cy, r, 0, Math.PI * 2);
      ctx.fillStyle = color + (status === 'healthy' ? 'CC' : 'FF');
      
      if (status === 'reconstructed') {
        ctx.shadowColor = 'rgba(139, 92, 246, 0.8)';
        ctx.shadowBlur = 10;
      } else {
        ctx.shadowColor = 'transparent';
        ctx.shadowBlur = 0;
      }
      
      ctx.fill();
      ctx.shadowColor = 'transparent';
      ctx.shadowBlur = 0;

      // State icon
      ctx.strokeStyle = '#ffffff';
      ctx.lineWidth = 1.5;
      ctx.lineCap = 'round';
      if (status === 'failed') drawCross(ctx, cx, cy, r);
      if (status === 'reconstructed') drawCheck(ctx, cx, cy, r);
    }

    animRef.current = requestAnimationFrame(draw);
  }, [layout, edges]);

  useEffect(() => {
    animRef.current = requestAnimationFrame(draw);
    return () => cancelAnimationFrame(animRef.current);
  }, [draw]);

  // Hit-test for hover & click
  const handleMouseMove = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const mx = (e.clientX - rect.left) * devicePixelRatio;
    const my = (e.clientY - rect.top) * devicePixelRatio;

    for (const node of layout) {
      const coord = coordsRef.current.get(node.id);
      if (!coord) continue;
      const { cx, cy } = coord;
      const dist = Math.sqrt((mx - cx) ** 2 + (my - cy) ** 2);
      if (dist < FAIL_R * 2.5) {
        const snap = snapshotRef.current;
        const id = String(node.id);
        setTooltip({
          x: e.clientX,
          y: e.clientY,
          sensor: {
            id: node.id,
            status: snap ? getSensorStatus(id, snap.masks, snap.reconstructions) : 'healthy',
            speed: snap?.readings[id] ?? null,
            reconstruction: snap?.reconstructions[id] ?? null,
            x: node.x,
            y: node.y,
          },
        });
        return;
      }
    }
    setTooltip(null);
  }, [layout]);

  const handleClick = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const mx = (e.clientX - rect.left) * devicePixelRatio;
    const my = (e.clientY - rect.top) * devicePixelRatio;

    for (const node of layout) {
      const coord = coordsRef.current.get(node.id);
      if (!coord) continue;
      const { cx, cy } = coord;
      const dist = Math.sqrt((mx - cx) ** 2 + (my - cy) ** 2);
      if (dist < FAIL_R * 2.5) {
        setSelectedSensor(node.id);
        return;
      }
    }
    setSelectedSensor(null);
  }, [layout, setSelectedSensor]);

  const activeFailed = snapshot ? Object.values(snapshot.masks).filter(Boolean).length : 0;
  const activeRecon = snapshot ? Object.keys(snapshot.reconstructions).length : 0;

  return (
    <div className="relative w-full h-full flex flex-col">
      {/* Legend */}
      <div className="absolute top-3 left-3 z-10 flex gap-4 bg-[#121820]/80 backdrop-blur-sm rounded px-3 py-1.5 text-[11px] font-mono border border-[#2A3545]">
        <LegendItem color="#10B981" label="Healthy" />
        <LegendItem color="#EF4444" label={`Failed (${activeFailed})`} />
        <LegendItem color="#8B5CF6" label={`Reconstructed (${activeRecon})`} />
      </div>

      {/* Canvas */}
      <div ref={wrapRef} className="flex-1 w-full">
        <canvas
          ref={canvasRef}
          className="w-full h-full cursor-crosshair"
          onMouseMove={handleMouseMove}
          onMouseLeave={() => setTooltip(null)}
          onClick={handleClick}
          aria-label={`Traffic sensor network. ${207 - activeFailed} of 207 sensors operational. ${activeFailed} failed, ${activeRecon} reconstructed by AI.`}
          role="img"
        />
      </div>

      {/* Tooltip */}
      {tooltip && (
        <div
          className="fixed z-50 pointer-events-none bg-[#1A2230] border border-[#2A3545] rounded shadow-xl p-3 text-xs font-mono"
          style={{ left: tooltip.x + 14, top: tooltip.y - 10 }}
        >
          <div className="text-[#8BA0BA] mb-1">SENSOR {tooltip.sensor.id}</div>
          <div className="flex items-center gap-1.5 mb-0.5">
            <span className={`inline-block w-2 h-2 rounded-full ${
              tooltip.sensor.status === 'healthy' ? 'bg-[#10B981]' :
              tooltip.sensor.status === 'failed' ? 'bg-[#EF4444]' : 'bg-[#8B5CF6]'
            }`} />
            <span className="text-[#E8EDF4] uppercase font-semibold">{tooltip.sensor.status}</span>
          </div>
          {tooltip.sensor.speed != null && (
            <div className="text-[#8BA0BA]">Speed: <span className="text-[#E8EDF4]">{tooltip.sensor.speed.toFixed(1)} mph</span></div>
          )}
          {tooltip.sensor.reconstruction != null && (
            <div className="text-[#8B5CF6]">AI Est: {tooltip.sensor.reconstruction.toFixed(1)} mph</div>
          )}
          <div className="text-[#2A3545] mt-1">Click to inspect</div>
        </div>
      )}
    </div>
  );
}

function LegendItem({ color, label }: { color: string; label: string }) {
  return (
    <div className="flex items-center gap-1.5">
      <div className="w-2 h-2 rounded-full" style={{ backgroundColor: color }} />
      <span className="text-[#8BA0BA]">{label}</span>
    </div>
  );
}
