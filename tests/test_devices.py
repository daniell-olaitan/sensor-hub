"""
Device management tests.
"""


def test_register_device(client, unique_id):
    """Device registration creates new device with unique ID."""
    response = client.post(
        "/devices",
        json={
            "serial_number": f"SN-{unique_id}",
            "device_type": "sensor",
            "firmware_version": "1.0.0",
        },
        headers={"idempotency-key": f"reg-{unique_id}"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["serial_number"] == f"SN-{unique_id}"
    assert data["device_type"] == "sensor"
    assert data["status"] == "registered"


def test_register_duplicate_serial_returns_existing(client, unique_id):
    """Registering same serial number returns existing device."""
    serial = f"SN-{unique_id}"

    response1 = client.post(
        "/devices",
        json={
            "serial_number": serial,
            "device_type": "sensor",
            "firmware_version": "1.0.0",
        },
        headers={"idempotency-key": f"reg1-{unique_id}"},
    )
    device_id_1 = response1.json()["id"]

    response2 = client.post(
        "/devices",
        json={
            "serial_number": serial,
            "device_type": "gateway",
            "firmware_version": "2.0.0",
        },
        headers={"idempotency-key": f"reg2-{unique_id}"},
    )
    device_id_2 = response2.json()["id"]

    assert device_id_1 == device_id_2


def test_get_device(client, unique_id):
    """Get device returns device details."""
    response = client.post(
        "/devices",
        json={
            "serial_number": f"SN-{unique_id}",
            "device_type": "sensor",
            "firmware_version": "1.0.0",
        },
        headers={"idempotency-key": f"reg-{unique_id}"},
    )
    device_id = response.json()["id"]

    get_response = client.get(f"/devices/{device_id}")
    assert get_response.status_code == 200
    assert get_response.json()["id"] == device_id


def test_update_device(client, unique_id):
    """Update device modifies device attributes."""
    response = client.post(
        "/devices",
        json={
            "serial_number": f"SN-{unique_id}",
            "device_type": "sensor",
            "firmware_version": "1.0.0",
        },
        headers={"idempotency-key": f"reg-{unique_id}"},
    )
    device_id = response.json()["id"]

    update_response = client.patch(
        f"/devices/{device_id}",
        json={"location": "Building A"},
    )

    assert update_response.status_code == 200
    assert update_response.json()["location"] == "Building A"


def test_list_devices(client, unique_id):
    """List devices returns registered devices."""
    for i in range(3):
        client.post(
            "/devices",
            json={
                "serial_number": f"SN-{unique_id}-{i}",
                "device_type": "sensor",
                "firmware_version": "1.0.0",
            },
            headers={"idempotency-key": f"reg-{unique_id}-{i}"},
        )

    response = client.get("/devices")
    assert response.status_code == 200
    assert len(response.json()) >= 3
