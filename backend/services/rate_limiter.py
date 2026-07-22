import time
from collections import deque

class RateLimiter:
    """
    In-memory rolling window rate limiter.
    """
    def __init__(self, max_requests: int = 10, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: deque[float] = deque()

    def allow(self) -> bool:
        now = time.time()
        # Evict expired requests
        while self.requests and self.requests[0] < now - self.window_seconds:
            self.requests.popleft()
            
        if len(self.requests) < self.max_requests:
            self.requests.append(now)
            return True
        return False
