"""
Microservicio de referencia desarrollado en FastAPI con instrumentacion completa de OpenTelemetry.
Demuestra la emision coordinada de trazas OTLP, metricas y logs estructurados JSON con Trace-to-Logs.
"""

import time
import asyncio
from typing import Dict, Any
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from src.config import settings
from src.telemetry.tracer import init_tracer
from src.telemetry.metrics import init_metrics
from src.telemetry.logging import setup_logger
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

# Inicializar componentes de telemetria
tracer = init_tracer()
metrics_dict = init_metrics()
logger = setup_logger("order-service")

app = FastAPI(
    title="Order Processing Microservice",
    description="Microservicio de referencia con observabilidad nativa de OpenTelemetry",
    version=settings.service_version
)


class OrderRequest(BaseModel):
    customer_id: str
    items_count: int
    amount: float


@app.middleware("http")
async def telemetry_middleware(request: Request, call_next):
    start_time = time.time()
    path = request.url.path
    method = request.method

    response: Response = await call_next(request)

    duration = time.time() - start_time
    status_code = str(response.status_code)

    # Registrar metrica de conteo y duracion
    metrics_dict["http_requests_total"].add(
        1,
        {"method": method, "route": path, "status": status_code}
    )
    metrics_dict["http_request_duration_seconds"].record(
        duration,
        {"method": method, "route": path, "status": status_code}
    )

    return response


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": settings.service_name,
        "version": settings.service_version,
        "environment": settings.environment
    }


@app.get("/api/v1/orders")
def list_orders():
    with tracer.start_as_current_span("db.query_orders") as span:
        span.set_attribute("db.system", "postgresql")
        span.set_attribute("db.name", "orders_db")
        span.set_attribute("db.statement", "SELECT * FROM orders ORDER BY created_at DESC LIMIT 10")
        
        # Simular latencia de base de datos
        time.sleep(0.04)
        logger.info("Consulta de listado de ordenes ejecutada exitosamente")

    return [
        {"order_id": "ord_9901", "customer_id": "cust_44", "status": "completed", "amount": 120.50},
        {"order_id": "ord_9902", "customer_id": "cust_12", "status": "processing", "amount": 45.00}
    ]


@app.post("/api/v1/orders")
def create_order(order: OrderRequest):
    logger.info(f"Iniciando creacion de orden para el cliente {order.customer_id}")

    # Sub-span 1: Validacion de inventario
    with tracer.start_as_current_span("inventory.verify_stock") as span:
        span.set_attribute("inventory.items_count", order.items_count)
        time.sleep(0.02)
        if order.items_count > 50:
            span.set_status(Status(StatusCode.ERROR, "Stock insuficiente"))
            logger.warning(f"Stock insuficiente para {order.items_count} unidades")
            raise HTTPException(status_code=400, detail="Stock insuficiente para la cantidad solicitada")

    # Sub-span 2: Transaccion de pago
    with tracer.start_as_current_span("payment.authorize") as span:
        span.set_attribute("payment.amount", order.amount)
        span.set_attribute("payment.currency", "USD")
        time.sleep(0.06)
        logger.info(f"Autorizacion de pago por ${order.amount:.2f} confirmada")

    # Sub-span 3: Persistencia en base de datos
    with tracer.start_as_current_span("db.insert_order") as span:
        span.set_attribute("db.system", "postgresql")
        start_db = time.time()
        time.sleep(0.03)
        metrics_dict["db_query_duration_seconds"].record(time.time() - start_db, {"operation": "INSERT"})

    logger.info("Orden creada y persistida con exito en base de datos")
    return {"order_id": f"ord_{int(time.time())}", "status": "confirmed", "customer_id": order.customer_id}


@app.get("/simulate/slow")
def simulate_slow_transaction():
    """
    Ruta para simular cuello de botella y latencia prolongada para visualizacion en Grafana Tempo.
    """
    with tracer.start_as_current_span("external_service.heavy_computation") as span:
        span.set_attribute("operation.type", "batch_reconciliation")
        logger.warn("Iniciando procesamiento pesado con latencia simulada")
        time.sleep(1.5)
        span.add_event("Checkpoint alcanzado: calculo de reconciliacion completado al 50%")
        time.sleep(0.8)
        logger.info("Procesamiento pesado completado")

    return {"status": "delayed_operation_completed", "duration_seconds": 2.3}


@app.get("/simulate/error")
def simulate_error_cascade():
    """
    Ruta para simular una excepcion no controlada con trace status ERROR para inspeccion en Grafana.
    """
    with tracer.start_as_current_span("critical_operation.execute") as span:
        try:
            logger.error("Error critico detectado: Fallo de comunicacion con el proveedor externo de pagos")
            raise RuntimeError("Connection reset by peer: gateway.payments.internal:443")
        except Exception as exc:
            span.record_exception(exc)
            span.set_status(Status(StatusCode.ERROR, str(exc)))
            logger.exception("Excepcion capturada y registrada en el span actual")
            raise HTTPException(status_code=500, detail="Error interno en el procesamiento de la transaccion")
