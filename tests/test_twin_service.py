import pytest
from backend.services.twin_service import TwinService
from backend.core.exceptions import SensorNotFoundError, InvalidSimulationStepError

def test_twin_service_lifecycle():
    service = TwinService()
    service.initialize()
    
    assert service.state is not None
    assert service.state.num_nodes == service.stream.get_num_nodes()
    assert service.state.current_time_step == 24  # Primed with 25 steps (0 to 24)

    # Test stepping
    service.step(steps=2)
    assert service.state.current_time_step == 26

    # Test snapshot structure
    snap = service.get_snapshot()
    assert "current_time" in snap
    assert "readings" in snap
    assert "masks" in snap
    assert "reconstructions" in snap


def test_twin_service_failure_injection():
    service = TwinService()
    service.initialize()

    # Inject failure on a valid sensor
    sensor_id = 5
    duration = 10
    service.inject_failure(sensor_id=sensor_id, duration=duration)
    
    assert service.state.masks[sensor_id]
    assert service.state.failure_timers[sensor_id] == duration

    # Test step with active failure triggers reconstruction
    service.step(1)
    # The timer should decrement by 1
    assert service.state.failure_timers[sensor_id] == duration - 1
    # It should have a reconstructed value
    assert str(sensor_id) in service.state.reconstructions

    # Inject invalid sensor
    with pytest.raises(SensorNotFoundError):
        service.inject_failure(sensor_id=-1, duration=5)

    with pytest.raises(SensorNotFoundError):
        service.inject_failure(sensor_id=9999, duration=5)

    # Inject invalid duration
    with pytest.raises(InvalidSimulationStepError):
        service.inject_failure(sensor_id=5, duration=0)
