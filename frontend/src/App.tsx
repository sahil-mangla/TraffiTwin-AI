import { useEffect, useState } from 'react';
import { motion } from 'motion/react';
import { Header } from './components/Header';
import { NetworkGraph } from './components/NetworkGraph';
import { OperationsRail } from './components/OperationsRail';
import { EventTimeline } from './components/EventTimeline';
import { ControlDock } from './components/ControlDock';
import { IncidentDrawer } from './components/IncidentDrawer';
import { StorytellingBanner } from './components/StorytellingBanner';
import { BackendOfflineOverlay } from './components/BackendOfflineOverlay';
import { useSystemState } from './hooks/useSystemState';
import { useAutoPlay } from './hooks/useAutoPlay';
import { api } from './api/trafitwin';
import type { GraphLayoutNode, GraphEdge } from './types/api';

// Panel entrance animation variants
const panelVariants = {
  hidden: { opacity: 0, y: 12 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: {
      delay: i * 0.1,
      duration: 0.4,
      ease: 'easeOut' as const,
    },
  }),
};

function App() {
  const { refetch } = useSystemState();
  useAutoPlay(refetch);

  const [layout, setLayout] = useState<GraphLayoutNode[]>([]);
  const [edges, setEdges] = useState<GraphEdge[]>([]);
  const [layoutError, setLayoutError] = useState(false);

  // Load static graph layout once
  useEffect(() => {
    Promise.all([
      fetch('/graph_layout.json').then((r) => r.json()),
      api.getGraph()
    ])
      .then(([layoutData, graphData]) => {
        setLayout(layoutData);
        setEdges(graphData.edges);
      })
      .catch(() => {
        setLayoutError(true);
        // Fallback: circular layout for 207 nodes
        const fallback: GraphLayoutNode[] = Array.from({ length: 207 }, (_, i) => {
          const angle = (i / 207) * Math.PI * 2;
          return { id: i, x: 0.5 + 0.42 * Math.cos(angle), y: 0.5 + 0.42 * Math.sin(angle) };
        });
        setLayout(fallback);
      });
  }, []);

  return (
    <div className="h-screen flex flex-col overflow-hidden bg-[#0B0F14] text-[#E8EDF4]">
      {/* Offline overlay — blocks everything if backend is down */}
      <BackendOfflineOverlay />

      {/* Header */}
      <motion.div custom={0} variants={panelVariants} initial="hidden" animate="visible">
        <Header />
      </motion.div>

      {/* Main area */}
      <div className="flex-1 flex min-h-0">
        {/* Left 70%: Digital Twin + Event Timeline */}
        <div className="flex-1 flex flex-col min-w-0 min-h-0">
          {/* Digital Twin hero */}
          <motion.div
            custom={1}
            variants={panelVariants}
            initial="hidden"
            animate="visible"
            className="flex-1 relative min-h-0 p-3"
          >
            <div className="relative w-full h-full overflow-hidden rounded-xl border border-[#2A3545] bg-[#121820] shadow-[0_10px_30px_rgba(0,0,0,0.25)]">
              {layoutError && (
                <div className="absolute top-12 left-1/2 -translate-x-1/2 z-10 text-[11px] font-mono text-[#F59E0B] bg-[#F59E0B]/10 border border-[#F59E0B]/30 rounded px-3 py-1.5">
                  ⚠ Network topology unavailable — showing sensor positions only (circular layout)
                </div>
              )}
              <StorytellingBanner />
              {layout.length > 0 && <NetworkGraph layout={layout} edges={edges} />}
            </div>
          </motion.div>

          {/* Event Timeline — bottom strip */}
          <motion.div
            custom={2}
            variants={panelVariants}
            initial="hidden"
            animate="visible"
            className="h-48 border-t border-[#2A3545] shrink-0 relative z-10 shadow-[0_-10px_30px_rgba(0,0,0,0.15)] bg-[#0B0F14]"
          >
            <EventTimeline />
          </motion.div>
        </div>

        {/* Right 30%: Operations Rail */}
        <motion.div
          custom={3}
          variants={panelVariants}
          initial="hidden"
          animate="visible"
          className="w-72 xl:w-80 shrink-0"
        >
          <OperationsRail />
        </motion.div>
      </div>

      {/* Control Dock */}
      <motion.div custom={4} variants={panelVariants} initial="hidden" animate="visible">
        <ControlDock onStep={refetch} />
      </motion.div>

      {/* Incident Drawer (floating) */}
      <IncidentDrawer layout={layout} />
    </div>
  );
}

export default App;
