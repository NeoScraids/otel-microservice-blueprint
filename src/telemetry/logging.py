"""
Configuracion de logging estructurado en JSON con inyeccion de contexto OpenTelemetry (trace_id y span_id).
Permite correlacion cruzada nativa (Trace-to-Logs) en Grafana Loki y Grafana Tempo.
"""

import logging
import json
import sys
from datetime import datetime, timezone
from opentelemetry import trace
from src.config import settings


class JsonTraceFormatter(logging.Formatter):
    """
    Formateador de logs que serializa en JSON e inyecta automaticamente
    el trace_id y span_id del contexto activo de OpenTelemetry.
    """
    def format(self, record: logging.LogRecord) -> str:
        current_span = trace.get_current_span()
        span_context = current_span.get_span_context() if current_span else None

        trace_id = ""
        span_id = ""

        if span_context and span_context.is_valid:
            trace_id = format(span_context.trace_id, "032x")
            span_id = format(span_context.span_id, "016x")

        log_record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "service.name": settings.service_name,
            "service.version": settings.service_version,
            "environment": settings.environment,
            "trace_id": trace_id,
            "span_id": span_id
        }

        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_record, ensure_ascii=False)


def setup_logger(name: str = "microservice") -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, settings.log_level, logging.INFO))
    
    # Evitar duplicacion de manejadores
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JsonTraceFormatter())
        logger.addHandler(handler)
        logger.propagate = False

    return logger
