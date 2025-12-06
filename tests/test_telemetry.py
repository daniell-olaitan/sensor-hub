"""
Telemetry ingestion and query tests.
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


def test_ingest_telemetry_point(client, device_id):
    """Ingest single telemetry point."""
    response = client.post(
        "/telemetry/point",
        json={
            "device_id": device_id,
            "timestamp": datetime.utcnow().isoformat(),
            "metric": "temperature",
            "value": 25.5,
            "unit": "celsius",
        },
    )

    assert response.status_code == 202


def test_ingest_telemetry_batch(client, device_id):
    """Ingest batch of telemetry points."""
    response = client.post(
        "/telemetry/batch",
        json={
            "device_id": device_id,
            "points": [
                {
                    "device_id": device_id,
                    "timestamp": datetime.utcnow().isoformat(),
                    "metric": "temperature",
                    "value": 25.5,
                },
                {
                    "device_id": device_id,
                    "timestamp": datetime.utcnow().isoformat(),
                    "metric": "humidity",
                    "value": 60.0,
                },
            ],
        },
    )

    assert response.status_code == 202
    assert response.json()["count"] == 2


def test_query_telemetry(client, device_id):
    """Query telemetry returns ingested points."""
    client.post(
        "/telemetry/point",
        json={
            "device_id": device_id,
            "timestamp": datetime.utcnow().isoformat(),
            "metric": "temperature",
            "value": 25.5,
        },
    )

    response = client.get(f"/telemetry/{device_id}?metric=temperature")
    assert response.status_code == 200
    assert len(response.json()) > 0


def test_get_latest_telemetry(client, device_id):
    """Get latest telemetry returns most recent point."""
    client.post(
        "/telemetry/point",
        json={
            "device_id": device_id,
            "timestamp": datetime.utcnow().isoformat(),
            "metric": "temperature",
            "value": 25.5,
        },
    )

    response = client.get(f"/telemetry/{device_id}/temperature/latest")
    assert response.status_code == 200
    assert response.json()["metric"] == "temperature"
