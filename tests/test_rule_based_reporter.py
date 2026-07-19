from backend.services.rule_based_reporter import RuleBasedReporter


def test_sensor_failure_with_reconstruction():
    reporter = RuleBasedReporter()
    report = reporter.generate_report({
        "sensor_id": 5,
        "event_type": "sensor_failure",
        "observability": 98.0,
        "neighbor_speed_change_pct": -2.0,
        "reconstructed": True,
        "affected_neighbors": [1, 2, 3],
    })
    assert "Sensor 5" in report
    assert "restored observability" in report
    assert "Operational" in report
    assert "stable conditions" in report


def test_sensor_failure_without_reconstruction():
    reporter = RuleBasedReporter()
    report = reporter.generate_report({
        "sensor_id": 7,
        "event_type": "sensor_failure",
        "observability": 92.0,
        "neighbor_speed_change_pct": -10.0,
        "reconstructed": False,
        "affected_neighbors": [],
    })
    assert "No reconstruction was possible" in report
    assert "Degraded" in report
    assert "moderate congestion propagation" in report


def test_sensor_recovery():
    reporter = RuleBasedReporter()
    report = reporter.generate_report({
        "sensor_id": 3,
        "event_type": "sensor_recovery",
        "observability": 99.5,
    })
    assert "Sensor 3 has recovered" in report
    assert "Operational" in report


def test_observability_drop_critical_and_severe_congestion():
    reporter = RuleBasedReporter()
    report = reporter.generate_report({
        "event_type": "observability_drop",
        "observability": 80.0,
        "neighbor_speed_change_pct": -20.0,
        "active_failures": 12,
    })
    assert "Network Alert" in report
    assert "Critical" in report
    assert "severe local congestion" in report
    assert "12 active failures" in report


def test_unknown_event_type_uses_default_branch():
    reporter = RuleBasedReporter()
    report = reporter.generate_report({
        "event_type": "system_check",
        "observability": 100.0,
    })
    assert "System Event: System check" in report
    assert "Operational" in report


def test_defaults_when_fields_missing():
    reporter = RuleBasedReporter()
    # No observability/speed_change/reconstructed keys at all.
    report = reporter.generate_report({"event_type": "sensor_recovery"})
    assert "100.0%" in report
    assert "Operational" in report
