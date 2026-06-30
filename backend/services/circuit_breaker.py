import time
import logging

logger = logging.getLogger(__name__)

class CircuitBreaker:
    """
    Circuit Breaker for the Gemini API.
    """
    def __init__(self, max_failures: int = 3, cooldown_seconds: int = 600):
        self.max_failures = max_failures
        self.cooldown_seconds = cooldown_seconds
        self.failure_count = 0
        self.state = "CLOSED"  # "CLOSED", "OPEN", "HALF-OPEN"
        self.last_state_change = time.time()

    def is_open(self) -> bool:
        now = time.time()
        if self.state == "OPEN":
            if now - self.last_state_change >= self.cooldown_seconds:
                self.state = "HALF-OPEN"
                self.last_state_change = now
                logger.info("Circuit breaker entered HALF-OPEN state.")
                return False
            return True
        return False

    def record_success(self):
        self.failure_count = 0
        if self.state != "CLOSED":
            self.state = "CLOSED"
            self.last_state_change = time.time()
            logger.info("Circuit breaker closed successfully.")

    def record_failure(self):
        self.failure_count += 1
        logger.warning(f"Circuit breaker recorded failure {self.failure_count}/{self.max_failures}")
        if self.failure_count >= self.max_failures and self.state != "OPEN":
            self.state = "OPEN"
            self.last_state_change = time.time()
            logger.error("Circuit breaker opened due to consecutive failures.")
