from backend.services.metrics_service import MetricsService

def test_metrics_service_empty():
    ms = MetricsService()
    metrics = ms.get_metrics()
    assert metrics["fcr"] == 0.0
    assert metrics["mae"] == 0.0
    assert metrics["rmse"] == 0.0
    assert metrics["total_failures_simulated"] == 0


def test_metrics_service_calculations():
    ms = MetricsService(window_size=10)
    # y_true = [50, 45, 60]
    # y_pred = [48, 40, 58]
    # errors = [2, 5, 2] -> MAE = (2+5+2)/3 = 3.0
    # RMSE = sqrt((4 + 25 + 4)/3) = sqrt(11) = 3.3166
    # FCR: threshold = 5.0. Errors <= 5.0: all 3. FCR = 100.0
    
    ms.add_reconstructions(
        y_true_dict={"1": 50.0, "2": 45.0},
        y_pred_dict={"1": 48.0, "2": 40.0}
    )
    # total failures = 2
    ms.add_reconstructions(
        y_true_dict={"3": 60.0},
        y_pred_dict={"3": 58.0}
    )
    # total failures = 3

    metrics = ms.get_metrics()
    assert metrics["total_failures_simulated"] == 3
    assert abs(metrics["mae"] - 3.0) < 1e-4
    assert abs(metrics["rmse"] - 3.31662479) < 1e-4
    assert metrics["fcr"] == 100.0

    # Add reconstruction where error > 5.0
    ms.add_reconstructions(
        y_true_dict={"4": 50.0},
        y_pred_dict={"4": 44.0}  # error = 6.0
    )
    metrics = ms.get_metrics()
    # Now covered = 3 out of 4 (75%)
    assert metrics["fcr"] == 75.0
