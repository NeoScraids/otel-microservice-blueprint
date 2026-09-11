"""
Inicializacion y configuracion del proveedor de trazas distribuidas OpenTelemetry (TracerProvider).
"""

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.trace.sampling import ParentBasedTraceIdRatioBased, TraceIdRatioBased
from opentelemetry.sdk.resources import Resource
from opentelemetry.semconv.resource import ResourceAttributes

from src.config import settings


def init_tracer():
    """
    Inicializa el TracerProvider global con exportador OTLP hacia Grafana Alloy o Tempo.
    """
    resource = Resource.create({
        ResourceAttributes.SERVICE_NAME: settings.service_name,
        ResourceAttributes.SERVICE_VERSION: settings.service_version,
        ResourceAttributes.DEPLOYMENT_ENVIRONMENT: settings.environment,
        "telemetry.sdk.language": "python"
    })

    sampler = ParentBasedTraceIdRatioBased(TraceIdRatioBased(settings.sampling_ratio))
    provider = TracerProvider(resource=resource, sampler=sampler)

    # Intentar exportador OTLP (gRPC o HTTP)
    exporter = None
    if settings.otlp_protocol == "grpc":
        try:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
            exporter = OTLPSpanExporter(endpoint=settings.otlp_endpoint, insecure=True)
        except Exception:
            exporter = ConsoleSpanExporter()
    else:
        try:
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
            exporter = OTLPSpanExporter(endpoint=settings.otlp_endpoint)
        except Exception:
            exporter = ConsoleSpanExporter()

    processor = BatchSpanProcessor(exporter)
    provider.add_span_processor(processor)

    trace.set_tracer_provider(provider)
    return trace.get_tracer(settings.service_name, settings.service_version)
