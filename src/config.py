"""
Modulo de configuracion para el microservicio instrumentado con OpenTelemetry.
"""

import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    service_name: str = os.getenv("SERVICE_NAME", "order-processing-service")
    service_version: str = os.getenv("SERVICE_VERSION", "1.0.0")
    environment: str = os.getenv("ENVIRONMENT", "production")
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8080"))
    
    otlp_endpoint: str = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
    otlp_protocol: str = os.getenv("OTEL_EXPORTER_PROTOCOL", "grpc").lower()
    sampling_ratio: float = float(os.getenv("OTEL_SAMPLING_RATIO", "1.0"))
    log_level: str = os.getenv("LOG_LEVEL", "INFO").upper()


settings = Settings()
