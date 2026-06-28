import logging
from backend.twin.twin_state import TwinState
from backend.twin.stream_simulator import StreamSimulator
from backend.services.reconstruction_service import ReconstructionService
from backend.services.metrics_service import MetricsService

logger = logging.getLogger(__name__)

class TwinService:
    """
    Orchestrates the Digital Twin workflow: streaming, failing, and reconstructing.
    """
    def __init__(self):
        self.stream = StreamSimulator()
        self.state = None
        self.reconstructor = ReconstructionService()
        self.metrics = MetricsService()
        
    def initialize(self):
        """Load data and model."""
        self.reconstructor.load_model()
        self.stream.load_data()
        self.state = TwinState(num_nodes=self.stream.get_num_nodes(), history_size=25)
        
        # Prime the twin state with 25 steps so history is fully populated
        logger.info("Priming TwinState with initial history...")
        for _ in range(25):
            readings, timestamp = self.stream.step()
            self.state.update_readings(readings, timestamp)
            
    def step(self, steps: int = 1):
        """Advance the simulation by `steps`."""
        for _ in range(steps):
            # 1. Get next true readings
            readings, timestamp = self.stream.step()
            
            # 2. Update state history
            self.state.update_readings(readings, timestamp)
            
            # 3. Perform reconstruction for any active failures
            reconstructions = self.reconstructor.reconstruct(
                state=self.state, 
                A=self.stream.get_adjacency_matrix()
            )
            
            # 4. Save reconstructions to state
            self.state.reconstructions = reconstructions
            
            # 5. Update metrics
            # Get the ground truth dict for failed sensors
            y_true_dict = {}
            for sensor_id in reconstructions.keys():
                sid = int(sensor_id)
                y_true_dict[sensor_id] = float(readings[sid])
                
            self.metrics.add_reconstructions(y_true_dict, reconstructions)
            
    def inject_failure(self, sensor_id: int, duration: int):
        self.state.inject_failure(sensor_id, duration)
        
    def get_snapshot(self):
        return self.state.get_snapshot()
        
    def get_metrics(self):
        return self.metrics.get_metrics()
