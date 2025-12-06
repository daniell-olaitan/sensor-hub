"""
Alert rule and alert management tests.
"""

from datetime import datetime

import pytest


@pytest.fixture
def device_id(client, unique_id):
    response = client.post(
        "/devices",
        json={
            "serial_number": f"SN-{unique_id}",
            "device_type": "sensor",
            "firmware_version": "1.0.0",
        },
        headers={"idempotency-key": f"reg-{unique_id}"},
    )
    return response.json()["id"]


def test_create_alert_rule(client, device_id):
    """Create alert rule for device metric."""
    response = client.post(
        "/alerts/rules",
        json={
            "device_id": device_id,
            "metric": "temperature",
            "operator": "gt",
            "threshold": 30.0,
            "severity": "warning",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["metric"] == "temperature"
    assert data["threshold"] == 30.0


def test_list_alert_rules(client, device_id):
    """List alert rules returns created rules."""
    client.post(
        "/alerts/rules",
        json={
            "device_id": device_id,
            "metric": "temperature",
            "operator": "gt",
            "threshold": 30.0,
            "severity": "warning",
        },
    )

    response = client.get(f"/alerts/rules?device_id={device_id}")
    assert response.status_code == 200
    assert len(response.json()) > 0


def test_alert_triggered_on_threshold_exceeded(client, device_id):
    """Alert is triggered when telemetry exceeds threshold."""
    client.post(
        "/alerts/rules",
        json={
            "device_id": device_id,
            "metric": "temperature",
            "operator": "gt",
            "threshold": 30.0,
            "severity": "critical",
        },
    )

    client.post(
        "/telemetry/point",
        json={
            "device_id": device_id,
            "timestamp": datetime.utcnow().isoformat(),
            "metric": "temperature",
            "value": 35.0,
        },
    )

    import time

    time.sleep(0.2)

    response = client.get("/alerts")
    assert response.status_code == 200
    alerts = response.json()
    assert any(a["device_id"] == device_id for a in alerts)


def test_acknowledge_alert(client, device_id):
    """Acknowledge alert changes status."""
    client.post(
        "/alerts/rules",
        json={
            "device_id": device_id,
            "metric": "temperature",
            "operator": "gt",
            "threshold": 30.0,
            "severity": "critical",
        },
    )

    client.post(
        "/telemetry/point",
        json={
            "device_id": device_id,
            "timestamp": datetime.utcnow().isoformat(),
            "metric": "temperature",
            "value": 35.0,
        },
    )

    import time

    time.sleep(0.2)

    alerts_response = client.get("/alerts")
    alerts = alerts_response.json()

    if alerts:
        alert_id = alerts[0]["id"]
        ack_response = client.post(f"/alerts/{alert_id}/acknowledge")
        assert ack_response.status_code == 200
        assert ack_response.json()["status"] == "acknowledged"
