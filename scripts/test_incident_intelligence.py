import sys
import os
import asyncio
import unittest
from datetime import datetime

# Set python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.services.rate_limiter import RateLimiter
from backend.services.circuit_breaker import CircuitBreaker
from backend.services.rule_based_reporter import RuleBasedReporter
from backend.services.gemini_service import GeminiService
from backend.services.incident_intelligence_service import IncidentIntelligenceService
from backend.services.twin_service import TwinService

class TestIncidentIntelligence(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        # We initialize twin service but mock data loading or just initialize lightly
        self.twin = TwinService()
        self.twin.initialize()

    def test_rate_limiter(self):
        limiter = RateLimiter(max_requests=2, window_seconds=1)
        self.assertTrue(limiter.allow())
        self.assertTrue(limiter.allow())
        self.assertFalse(limiter.allow())  # 3rd should block

    def test_circuit_breaker(self):
        cb = CircuitBreaker(max_failures=3, cooldown_seconds=1)
        self.assertFalse(cb.is_open())
        cb.record_failure()
        cb.record_failure()
        cb.record_failure()
        self.assertTrue(cb.is_open())  # Open after 3 failures

    def test_rule_based_reporter(self):
        reporter = RuleBasedReporter()
        incident = {
            "sensor_id": 51,
            "event_type": "sensor_failure",
            "observability": 97.5,
            "neighbor_speed_change_pct": -8.5,
            "reconstructed": True,
            "affected_neighbors": [50, 52]
        }
        report = reporter.generate_report(incident)
        self.assertIn("Sensor 51", report)
        self.assertIn("moderate congestion propagation", report)
        self.assertIn("restored observability", report)
        self.assertIn("97.5%", report)

    async def test_offline_fallback(self):
        # No API Key provided: GeminiService should fall back to deterministic summarization
        gemini = GeminiService(api_key=None)
        service = IncidentIntelligenceService(gemini_service=gemini)
        
        # Ingest a failure
        self.twin.inject_failure(sensor_id=51, duration=3)
        summary = await service.process_event(self.twin, "sensor_failure", sensor_id=51, duration=3)
        
        self.assertIsNotNone(summary)
        self.assertIn("Sensor 51", summary)
        
        # Verify summaries cache
        summaries = service.get_latest_summaries()
        self.assertEqual(len(summaries), 1)
        self.assertFalse(summaries[0]["is_ai"])

if __name__ == '__main__':
    unittest.main()
