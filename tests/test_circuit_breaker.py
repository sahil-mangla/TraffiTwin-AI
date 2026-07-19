from backend.services.circuit_breaker import CircuitBreaker


def test_starts_closed():
    cb = CircuitBreaker(max_failures=3, cooldown_seconds=600)
    assert cb.state == "CLOSED"
    assert cb.is_open() is False


def test_opens_after_max_failures():
    cb = CircuitBreaker(max_failures=3, cooldown_seconds=600)
    cb.record_failure()
    cb.record_failure()
    assert cb.state == "CLOSED"
    assert cb.is_open() is False

    cb.record_failure()
    assert cb.state == "OPEN"
    assert cb.is_open() is True


def test_success_resets_failure_count_and_closes():
    cb = CircuitBreaker(max_failures=2, cooldown_seconds=600)
    cb.record_failure()
    cb.record_success()
    assert cb.failure_count == 0
    assert cb.state == "CLOSED"

    # One more failure shouldn't open it since the count was reset.
    cb.record_failure()
    assert cb.state == "CLOSED"


def test_transitions_to_half_open_after_cooldown():
    cb = CircuitBreaker(max_failures=1, cooldown_seconds=0)
    cb.record_failure()
    assert cb.state == "OPEN"

    # cooldown_seconds=0 means the very next check should allow a trial call.
    assert cb.is_open() is False
    assert cb.state == "HALF-OPEN"


def test_half_open_success_closes_circuit():
    cb = CircuitBreaker(max_failures=1, cooldown_seconds=0)
    cb.record_failure()
    cb.is_open()  # transitions to HALF-OPEN
    assert cb.state == "HALF-OPEN"

    cb.record_success()
    assert cb.state == "CLOSED"
    assert cb.failure_count == 0


def test_half_open_failure_reopens_circuit():
    cb = CircuitBreaker(max_failures=1, cooldown_seconds=0)
    cb.record_failure()
    cb.is_open()  # transitions to HALF-OPEN
    assert cb.state == "HALF-OPEN"

    cb.record_failure()
    assert cb.state == "OPEN"


def test_stays_open_before_cooldown_elapses():
    cb = CircuitBreaker(max_failures=1, cooldown_seconds=600)
    cb.record_failure()
    assert cb.is_open() is True
    assert cb.state == "OPEN"
