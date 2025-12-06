# SensorHub - IoT Platform

IoT platform for managing connected devices, processing telemetry, and coordinating firmware updates.

## Features

- Device lifecycle management
- Real-time telemetry ingestion (>10k msg/sec)
- Rule-based alerting with escalation
- Firmware update orchestration
- Fleet analytics and health monitoring

## Quick Start

```bash
pip install -e .
```

## API Endpoints

- `POST /devices` - Register device
- `GET /devices/{device_id}` - Get device details
- `POST /telemetry/batch` - Ingest telemetry batch
- `GET /telemetry/{device_id}` - Query device telemetry
- `POST /alerts/rules` - Create alert rule
- `GET /alerts` - List alerts
- `POST /firmware/updates` - Initiate firmware update
- `GET /firmware/updates/{update_id}` - Check update status
- `GET /analytics/fleet` - Fleet analytics
- `GET /health` - System health

## Architecture

- **FastAPI** application with async support
- **Redis** for caching, locking, and event storage
- **Event-driven** architecture with internal event bus
- **Saga pattern** for distributed transactions
- **Circuit breakers** for resilience
- **Rate limiting** and backpressure handling

## Testing

```bash
pytest tests/
```

## Configuration

See `app/config/settings.py` for environment variables.
```
