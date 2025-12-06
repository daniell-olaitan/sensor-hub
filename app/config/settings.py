from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    redis_url: str = "redis://localhost:6379"
    redis_max_connections: int = 50
    redis_socket_timeout: int = 5

    rate_limit_telemetry_per_device: int = 100
    rate_limit_window_seconds: int = 60
    rate_limit_global_per_second: int = 10000

    circuit_breaker_failure_threshold: int = 6
    circuit_breaker_timeout_seconds: int = 60
    circuit_breaker_half_open_max_calls: int = 3

    lock_timeout_seconds: int = 10
    lock_retry_delay_ms: int = 50

    telemetry_batch_max_size: int = 1000
    telemetry_retention_seconds: int = 86400

    event_bus_queue_max_size: int = 10000
    event_bus_worker_count: int = 4

    backpressure_queue_threshold: int = 8000
    backpressure_reject_threshold: int = 9500

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
