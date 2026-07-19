import time

from backend.services.rate_limiter import RateLimiter


def test_allows_up_to_max_requests():
    limiter = RateLimiter(max_requests=3, window_seconds=60)
    assert limiter.allow() is True
    assert limiter.allow() is True
    assert limiter.allow() is True
    assert limiter.allow() is False


def test_denies_beyond_max_requests_until_window_expires():
    limiter = RateLimiter(max_requests=1, window_seconds=0.1)
    assert limiter.allow() is True
    assert limiter.allow() is False

    time.sleep(0.15)
    assert limiter.allow() is True


def test_independent_limiters_do_not_share_state():
    a = RateLimiter(max_requests=1, window_seconds=60)
    b = RateLimiter(max_requests=1, window_seconds=60)

    assert a.allow() is True
    assert b.allow() is True
    assert a.allow() is False
    assert b.allow() is False


def test_evicts_only_expired_requests():
    limiter = RateLimiter(max_requests=2, window_seconds=0.1)
    assert limiter.allow() is True
    time.sleep(0.15)
    # The first request has now expired; a fresh one should be allowed.
    assert limiter.allow() is True
    assert limiter.allow() is True
    assert limiter.allow() is False
