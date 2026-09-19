"""
Inicializacion de metricas OpenTelemetry y exportacion OTLP hacia Prometheus / Mimir.
"""

from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader, ConsoleMetricExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.semconv.resource import ResourceAttributes

from src.config import settings


def init_metrics():
    """
    Inicializa el MeterProvider global con recolector OTLP de metricas.
    """
    resource = Resource.create({
        ResourceAttributes.SERVICE_NAME: settings.service_name,
        ResourceAttributes.SERVICE_VERSION: settings.service_version,
        ResourceAttributes.DEPLOYMENT_ENVIRONMENT: settings.environment,
    })

    reader = None
    try:
        if settings.otlp_protocol == "grpc":
            from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
            exporter = OTLPMetricExporter(endpoint=settings.otlp_endpoint, insecure=True)
        else:
            from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
            exporter = OTLPMetricExporter(endpoint=f"{settings.otlp_endpoint}/v1/metrics")
        reader = PeriodicExportingMetricReader(exporter, export_interval_millis=15000)
    except Exception:
        reader = PeriodicExportingMetricReader(ConsoleMetricExporter(), export_interval_millis=60000)

    provider = MeterProvider(resource=resource, metric_readers=[reader])
    metrics.set_meter_provider(provider)

    meter = metrics.get_meter(settings.service_name, settings.service_version)

    # Metricas de aplicacion
    http_requests_total = meter.create_counter(
        name="http_requests_total",
        description="Total de peticiones HTTP procesadas por ruta y estado",
        unit="1"
    )

    http_request_duration_seconds = meter.create_histogram(
        name="http_request_duration_seconds",
        description="Histograma de duracion de solicitudes HTTP",
        unit="s"
    )

    db_query_duration_seconds = meter.create_histogram(
        name="db_query_duration_seconds",
        description="Tiempo de ejecucion de consultas a la capa de persistencia",
        unit="s"
    )

    # UpDownCounter: solicitudes HTTP activas en vuelo en este momento.
    # Se incrementa al inicio de cada request y se decrementa al finalizar
    # (en el middleware de telemetria). Util para detectar stalls y thread
    # exhaustion antes de que se manifiesten como errores HTTP 503/504.
    active_requests_gauge = meter.create_up_down_counter(
        name="http_active_requests",
        description="Numero de solicitudes HTTP actualmente en procesamiento",
        unit="1"
    )

    return {
        "meter": meter,
        "http_requests_total": http_requests_total,
        "http_request_duration_seconds": http_request_duration_seconds,
        "db_query_duration_seconds": db_query_duration_seconds,
        "active_requests_gauge": active_requests_gauge,
    }
