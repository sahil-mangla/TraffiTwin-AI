class TraffiTwinException(Exception):
    """Base exception for TraffiTwin application"""
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class SensorNotFoundError(TraffiTwinException):
    """Raised when a sensor is not found or the sensor ID is out of bounds"""
    def __init__(self, sensor_id: int):
        super().__init__(f"Sensor with ID {sensor_id} not found", status_code=404)
        self.sensor_id = sensor_id


class InvalidSimulationStepError(TraffiTwinException):
    """Raised when the simulation step argument is invalid"""
    def __init__(self, message: str):
        super().__init__(message, status_code=422)


class ServiceUnavailableError(TraffiTwinException):
    """Raised when the requested backend service is not initialized"""
    def __init__(self, service_name: str):
        super().__init__(f"Service '{service_name}' is not initialized", status_code=503)
