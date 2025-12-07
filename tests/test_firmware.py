"""
Firmware update tests.
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


@pytest.fixture
def firmware_version(client, unique_id):
    version = f"2.0.{unique_id[:4]}"
    client.post(
        "/firmware/register",
        json={
            "version": version,
            "size_bytes": 1024000,
            "checksum": f"sha256-{unique_id}",
            "release_notes": "Test version",
            "min_compatible_version": "1.0.0",
            "created_at": datetime.utcnow().isoformat(),
        },
    )
    return version


def test_register_firmware(client, unique_id):
    """Register new firmware version."""
    version = f"2.0.{unique_id[:4]}"
    response = client.post(
        "/firmware/register",
        json={
            "version": version,
            "size_bytes": 1024000,
            "checksum": f"sha256-{unique_id}",
            "release_notes": "Test version",
            "min_compatible_version": "1.0.0",
            "created_at": datetime.utcnow().isoformat(),
        },
    )

    assert response.status_code == 201
    assert response.json()["version"] == version


def test_initiate_firmware_update(client, device_id, firmware_version):
    """Initiate firmware update for device."""
    response = client.post(
        "/firmware/updates",
        json={
            "device_id": device_id,
            "to_version": firmware_version,
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["device_id"] == device_id
    assert data["to_version"] == firmware_version
    assert data["status"] in ["pending", "downloading"]


def test_get_update_status(client, device_id, firmware_version):
    """Get firmware update status."""
    create_response = client.post(
        "/firmware/updates",
        json={
            "device_id": device_id,
            "to_version": firmware_version,
        },
    )
    update_id = create_response.json()["id"]

    response = client.get(f"/firmware/updates/{update_id}")
    assert response.status_code == 200
    assert response.json()["id"] == update_id
