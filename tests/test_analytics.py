"""
Analytics and metrics tests.
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
            "group_id": f"group-{unique_id}",
        },
        headers={"idempotency-key": f"reg-{unique_id}"},
    )
    return response.json()["id"]


def test_get_device_metrics(client, device_id):
    """Get metrics for specific device."""
    client.post(
        "/telemetry/point",
        json={
            "device_id": device_id,
            "timestamp": datetime.utcnow().isoformat(),
            "metric": "temperature",
            "value": 25.5,
        },
    )

    response = client.get(f"/analytics/devices/{device_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["device_id"] == device_id
    assert data["message_count"] >= 1


def test_get_fleet_analytics(client, device_id):
    """Get fleet-wide analytics."""
    response = client.get("/analytics/fleet")
    assert response.status_code == 200
    data = response.json()
    assert "total_devices" in data
    assert "active_devices" in data
    assert data["total_devices"] >= 1


def test_get_group_analytics(client, device_id, unique_id):
    """Get analytics for device group."""
    group_id = f"group-{unique_id}"

    response = client.get(f"/analytics/groups/{group_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["group_id"] == group_id
    assert data["device_count"] >= 1
