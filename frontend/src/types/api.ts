// ── Shared API types matching backend schemas ────────────────────────────────

export interface TwinSnapshot {
  current_time: number;
  readings: Record<string, number>;    // sensor_id → speed mph
  masks: Record<string, boolean>;      // sensor_id → true if failed
  reconstructions: Record<string, number>; // sensor_id → ai estimate
}

export interface TwinMetrics {
  fcr: number;
  mae: number;
  rmse: number;
  total_failures_simulated: number;
}

export interface SystemState {
  snapshot: TwinSnapshot;
  metrics: TwinMetrics;
  timestamp: string;
  system_health: 'healthy' | 'degraded' | 'critical';
}

export interface GraphNode {
  id: number;
}

export interface GraphEdge {
  source: number;
  target: number;
  weight: number;
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface GraphLayoutNode {
  id: number;
  x: number;  // normalised 0–1
  y: number;  // normalised 0–1
}

// ── Frontend-only types ──────────────────────────────────────────────────────

export type EventSeverity = 'FAULT' | 'AI_RESPONSE' | 'RECOVERY' | 'SYSTEM';

export interface TwinEvent {
  id: string;
  timestamp: string;
  severity: EventSeverity;
  message: string;
  sensor_id?: number;
}

export type NodeStatus = 'healthy' | 'failed' | 'reconstructed';

export interface SensorInfo {
  id: number;
  status: NodeStatus;
  speed: number | null;
  reconstruction: number | null;
  x: number;
  y: number;
}
