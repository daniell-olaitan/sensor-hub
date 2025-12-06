"""
End-to-end integration tests.
"""

import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime


def test_complete_device_lifecycle(client, unique_id):
    """Test complete device lifecycle from registration to decommission."""
    register_response = client.post(
        "/devices",
        json={
            "serial_number": f"SN-{unique_id}",
            "device_type": "sensor",
            "firmware_version": "1.0.0",
        },
        headers={"idempotency-key": f"reg-{unique_id}"},
    )
    assert register_response.status_code == 201
    device_id = register_response.json()["id"]

    client.post(
        "/telemetry/point",
        json={
            "device_id": device_id,
            "timestamp": datetime.utcnow().isoformat(),
            "metric": "temperature",
            "value": 25.5,
        },
    )

    get_response = client.get(f"/devices/{device_id}")
    assert get_response.json()["status"] == "active"

    update_response = client.patch(
        f"/devices/{device_id}",
        json={"status": "inactive"},
    )
    assert update_response.json()["status"] == "inactive"


def test_telemetry_to_alert_flow(client, unique_id):
    """Test telemetry ingestion triggers alert."""
    device_response = client.post(
        "/devices",
        json={
            "serial_number": f"SN-{unique_id}",
            "device_type": "sensor",
            "firmware_version": "1.0.0",
        },
        headers={"idempotency-key": f"reg-{unique_id}"},
    )
    device_id = device_response.json()["id"]

    rule_response = client.post(
        "/alerts/rules",
        json={
            "device_id": device_id,
            "metric": "temperature",
            "operator": "gt",
            "threshold": 30.0,
            "severity": "critical",
        },
    )
    assert rule_response.status_code == 201

    client.post(
        "/telemetry/point",
        json={
            "device_id": device_id,
            "timestamp": datetime.utcnow().isoformat(),
            "metric": "temperature",
            "value": 35.0,
        },
    )

    time.sleep(0.2)

    alerts_response = client.get("/alerts")
    alerts = [a for a in alerts_response.json() if a["device_id"] == device_id]
    assert len(alerts) > 0


def test_concurrent_telemetry_ingestion(client, unique_id):
    """Test concurrent telemetry ingestion from multiple devices."""
    device_ids = []
    for i in range(5):
        response = client.post(
            "/devices",
            json={
                "serial_number": f"SN-{unique_id}-{i}",
                "device_type": "sensor",
                "firmware_version": "1.0.0",
            },
            headers={"idempotency-key": f"reg-{unique_id}-{i}"},
        )
        device_ids.append(response.json()["id"])

    def send_telemetry(device_id):
        return client.post(
            "/telemetry/batch",
            json={
                "device_id": device_id,
                "points": [
                    {
                        "device_id": device_id,
                        "timestamp": datetime.utcnow().isoformat(),
                        "metric": "temperature",
                        "value": 25.0 + i,
                    }
                    for i in range(10)
                ],
            },
        )

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(send_telemetry, did) for did in device_ids]
        results = [f.result() for f in futures]

    assert all(r.status_code == 202 for r in results)


def test_high_volume_telemetry_with_rate_limiting(client, unique_id):
    """Test rate limiting under high volume."""
    device_response = client.post(
        "/devices",
        json={
            "serial_number": f"SN-{unique_id}",
            "device_type": "sensor",
            "firmware_version": "1.0.0",
        },
        headers={"idempotency-key": f"reg-{unique_id}"},
    )
    device_id = device_response.json()["id"]

    responses = []
    for i in range(150):
        response = client.post(
            "/telemetry/point",
            json={
                "device_id": device_id,
                "timestamp": datetime.utcnow().isoformat(),
                "metric": "temperature",
                "value": 25.0,
            },
        )
        responses.append(response.status_code)

    success_count = responses.count(202)
    rate_limited_count = responses.count(429) + responses.count(400)

    print(f"Success: {success_count}, Rate limited: {rate_limited_count}")

    assert success_count > 0, "Some requests should succeed"
    assert rate_limited_count > 0, "Some requests should be rate limited"
    assert success_count <= 105, (
        f"Rate limit should prevent excessive requests (got {success_count})"
    )
