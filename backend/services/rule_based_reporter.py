from typing import Dict, Any

class RuleBasedReporter:
    """
    Offline, deterministic rule-based summary reporter.
    """
    def generate_report(self, incident: Dict[str, Any]) -> str:
        sensor_id = incident.get("sensor_id")
        event_type = incident.get("event_type")
        observability = incident.get("observability", 100.0)
        speed_change = incident.get("neighbor_speed_change_pct", 0.0)
        reconstructed = incident.get("reconstructed", False)
        
        # Determine network status
        if observability >= 95:
            network_status = "Operational"
        elif 90 <= observability < 95:
            network_status = "Degraded"
        else:
            network_status = "Critical"
            
        # Determine congestion severity
        if speed_change > -5.0:
            congestion_desc = "stable conditions"
        elif -15.0 <= speed_change <= -5.0:
            congestion_desc = "moderate congestion propagation"
        else:
            congestion_desc = "severe local congestion"

        affected_neighbors = len(incident.get("affected_neighbors", []))

        # Format incident reports based on event type
        if event_type == "sensor_failure":
            recon_msg = (
                "TraffiTwin successfully restored observability using virtual sensing."
                if reconstructed
                else "No reconstruction was possible for this node."
            )
            report = (
                f"Sensor {sensor_id} experienced a communication outage. "
                f"{affected_neighbors} neighboring sensors remained operational and enabled virtual reconstruction. "
                f"Traffic conditions indicate {congestion_desc}. "
                f"{recon_msg} "
                f"Current network observability remains {observability:.1f}% and network status is {network_status}."
            )
        elif event_type == "sensor_recovery":
            report = (
                f"Sensor {sensor_id} has recovered and returned to nominal service. "
                f"Virtual sensing has disengaged for this node. "
                f"Current network observability is {observability:.1f}% and network status is {network_status}."
            )
        elif event_type == "observability_drop":
            report = (
                f"Network Alert: Observability dropped significantly. "
                f"Current network observability is {observability:.1f}% and network status is {network_status}. "
                f"Traffic conditions indicate {congestion_desc} with {incident.get('active_failures', 0)} active failures."
            )
        else:
            report = (
                f"System Event: {str(event_type).replace('_', ' ').capitalize()}. "
                f"Current network observability is {observability:.1f}% and network status is {network_status}."
            )
            
        return report
