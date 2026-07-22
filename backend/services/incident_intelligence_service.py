import time
import logging
import numpy as np
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from backend.services.rate_limiter import RateLimiter
from backend.services.circuit_breaker import CircuitBreaker
from backend.services.rule_based_reporter import RuleBasedReporter
from backend.services.gemini_service import GeminiService
from backend.services.twin_service import TwinService

logger = logging.getLogger(__name__)

class EventDeduplicator:
    """
    Prevents repeated calls for identical events within a short TTL.
    """
    def __init__(self, ttl: float = 120.0):
        self.ttl = ttl
        self.cache: Dict[str, float] = {}  # key -> timestamp

    def is_duplicate(self, event_type: str, sensor_id: Optional[int]) -> bool:
        now = time.time()
        key = f"{event_type}:{sensor_id}"
        # Prune expired keys
        self.cache = {k: ts for k, ts in self.cache.items() if now - ts < self.ttl}
        
        if key in self.cache:
            return True
        self.cache[key] = now
        return False

class IncidentIntelligenceService:
    """
    Orchestrator for deterministic & AI incident summary reporting.
    """
    def __init__(self, gemini_service: Optional[GeminiService] = None):
        self.rate_limiter = RateLimiter(max_requests=10, window_seconds=60)
        self.circuit_breaker = CircuitBreaker(max_failures=3, cooldown_seconds=600)
        self.rule_based_reporter = RuleBasedReporter()
        self.gemini_service = gemini_service or GeminiService()
        self.deduplicator = EventDeduplicator(ttl=120.0)
        
        # Latest 20 summaries
        self.summaries_cache: List[Dict[str, Any]] = []
        self.latest_summary_text: Optional[str] = None

    def get_latest_summaries(self) -> List[Dict[str, Any]]:
        return self.summaries_cache

    def get_latest_summary_text(self) -> Optional[str]:
        return self.latest_summary_text

    def clear_latest_summary(self):
        self.latest_summary_text = None

    def build_incident_object(self, twin: TwinService, event_type: str, sensor_id: Optional[int] = None, duration: Optional[int] = None) -> Dict[str, Any]:
        snapshot = twin.get_snapshot()
        metrics = twin.get_metrics()
        
        active_failures = sum(1 for v in snapshot["masks"].values() if v)
        reconstructed_nodes = len(snapshot["reconstructions"])
        
        num_nodes = twin.state.num_nodes
        observability = ((num_nodes - active_failures + reconstructed_nodes) / num_nodes) * 100.0

        affected_neighbors = []
        speed_change = 0.0
        
        if sensor_id is not None:
            A = twin.stream.get_adjacency_matrix()
            if 0 <= sensor_id < len(A):
                # Get neighbor indices
                affected_neighbors = [j for j in range(len(A)) if A[sensor_id, j] > 0 and j != sensor_id]
                
            if affected_neighbors:
                current_speeds = twin.state.history[-1, affected_neighbors]
                hist_speeds = twin.state.history[:-1, affected_neighbors]
                # Avoid divide by zero/nan issues
                mean_hist = np.nanmean(hist_speeds, axis=0)
                
                pct_changes = []
                for i, neighbor_idx in enumerate(affected_neighbors):
                    cur = current_speeds[i]
                    hist = mean_hist[i]
                    if not np.isnan(cur) and not np.isnan(hist) and hist > 0:
                        pct_changes.append(((cur - hist) / hist) * 100)
                
                if pct_changes:
                    speed_change = float(np.mean(pct_changes))

        if observability >= 95:
            network_status = "Operational"
        elif 90 <= observability < 95:
            network_status = "Degraded"
        else:
            network_status = "Critical"

        incident_id = f"inc-{int(time.time())}-{sensor_id if sensor_id is not None else 'sys'}"
        
        return {
            "incident_id": incident_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "sensor_id": sensor_id,
            "event_type": event_type,
            "failure_duration_minutes": float(duration * 5) if duration else 0.0,
            "reconstructed": str(sensor_id) in snapshot["reconstructions"] if sensor_id is not None else False,
            "observability": float(observability),
            "mae": float(metrics.get("mae", 0.0)),
            "rmse": float(metrics.get("rmse", 0.0)),
            "active_failures": int(active_failures),
            "reconstructed_nodes": int(reconstructed_nodes),
            "affected_neighbors": [int(n) for n in affected_neighbors],
            "neighbor_speed_change_pct": float(speed_change),
            "network_status": network_status,
        }

    async def process_event(self, twin: TwinService, event_type: str, sensor_id: Optional[int] = None, duration: Optional[int] = None) -> str:
        """
        Creates an incident, evaluates through rules, rate limits, circuit breaker,
        attempts Gemini call, and saves to cache.
        """
        incident = self.build_incident_object(twin, event_type, sensor_id, duration)
        deterministic_report = self.rule_based_reporter.generate_report(incident)

        is_ai = False
        final_summary = deterministic_report
        meaningful_events = ["sensor_failure", "sensor_recovery", "observability_drop"]
        
        if event_type in meaningful_events:
            # Check deduplicator
            if not self.deduplicator.is_duplicate(event_type, sensor_id):
                # Check rate limiter
                if self.rate_limiter.allow():
                    # Check circuit breaker
                    if not self.circuit_breaker.is_open():
                        try:
                            logger.info(f"Requesting Gemini enrichment for event: {event_type} (Sensor {sensor_id})")
                            enriched = await self.gemini_service.enrich_report(incident, deterministic_report)
                            self.circuit_breaker.record_success()
                            final_summary = enriched
                            is_ai = True
                        except Exception as e:
                            logger.error(f"Gemini enrichment failed. Falling back. Error: {e}")
                            self.circuit_breaker.record_failure()
                    else:
                        logger.warning("Circuit breaker is OPEN. Falling back to deterministic summary.")
                else:
                    logger.warning("Rate limit hit. Falling back to deterministic summary.")
            else:
                logger.info(f"Duplicate event {event_type} on Sensor {sensor_id} detected. Skipping Gemini.")

        self.cache_report(incident, final_summary, is_ai)
        self.latest_summary_text = final_summary
        return final_summary

    def cache_report(self, incident: dict, summary: str, is_ai: bool):
        entry = {
            "incident_id": incident["incident_id"],
            "timestamp": incident["timestamp"],
            "sensor_id": incident["sensor_id"],
            "event_type": incident["event_type"],
            "summary": summary,
            "payload": incident,
            "is_ai": is_ai
        }
        self.summaries_cache.insert(0, entry)
        self.summaries_cache = self.summaries_cache[:20]

    async def generate_from_payload(self, incident: dict) -> str:
        """
        Manually generate a report from a raw payload (used by POST /generate-incident-summary).
        """
        deterministic_report = self.rule_based_reporter.generate_report(incident)
        if not self.rate_limiter.allow() or self.circuit_breaker.is_open():
            self.latest_summary_text = deterministic_report
            return deterministic_report
            
        try:
            enriched = await self.gemini_service.enrich_report(incident, deterministic_report)
            self.circuit_breaker.record_success()
            self.latest_summary_text = enriched
            return enriched
        except Exception:
            self.circuit_breaker.record_failure()
            self.latest_summary_text = deterministic_report
            return deterministic_report
