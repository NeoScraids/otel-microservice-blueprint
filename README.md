# otel-microservice-blueprint

Microservicio en FastAPI instrumentado con OpenTelemetry desde cero. Exporta trazas (OTLP), metricas (contadores + histogramas) y logs en JSON con `trace_id` y `span_id` inyectados automaticamente para que la correlacion en Grafana funcione de verdad.

Lo arme porque cada vez que necesitaba probar algo en el stack de observabilidad (un nuevo dashboard, una regla de alerting, la configuracion de Alloy) tenia que generar trafico real o inventar algo rapido. Esto es ese "algo rapido" pero hecho bien.

## Que tiene

**Endpoints del microservicio:**

- `GET /health` - Health check basico
- `GET /api/v1/orders` - Simula query a base de datos (genera span `db.query_orders`)
- `POST /api/v1/orders` - Flujo completo: validacion de inventario -> autorizacion de pago -> insert en BD. Genera 3 sub-spans encadenados.
- `GET /simulate/slow` - Operacion lenta (2.3s) para ver flame graphs en Tempo
- `GET /simulate/error` - Excepcion controlada con span status ERROR y stack trace registrado

**Generador de carga** (`load_generator.py`): Manda peticiones mezclando los endpoints anteriores con distribucion realista (65% orders, 20% list, 10% slow, 5% errors).

## Formato del log

Cada linea de log sale asi:

```json
{
  "timestamp": "2026-09-10T20:45:00Z",
  "level": "INFO",
  "message": "Autorizacion de pago por $120.50 confirmada",
  "service.name": "order-processing-service",
  "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
  "span_id": "00f067aa0ba902b7"
}
```

Con esto, en Loki configuras un `derivedField` que extraiga `trace_id` y te linkea directo a la traza en Tempo. Sin ese campo en el log, la correlacion Trace-to-Logs no funciona.

## Como usarlo

```bash
git clone https://github.com/NeoScraids/otel-microservice-blueprint.git
cd otel-microservice-blueprint
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

# Levantar el microservicio
uvicorn src.main:app --host 0.0.0.0 --port 8080

# En otra terminal, generar trafico
python load_generator.py 50
```

Si tenes el [observability-lgtm-stack](https://github.com/NeoScraids/observability-lgtm-stack) corriendo, apunta el exporter a Alloy (`OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317`) y vas a ver las trazas en Tempo y los logs en Loki inmediatamente.

## Con Docker

```bash
docker build -t otel-microservice:latest .
```

Si usas la red del stack de observabilidad:
```bash
docker compose up -d  # Requiere que exista la red 'observability-net'
```

## Estructura

```
src/
  config.py              # Settings via .env
  main.py                # FastAPI app + endpoints + middleware de metricas
  telemetry/
    tracer.py            # TracerProvider + exportador OTLP
    metrics.py           # MeterProvider + contadores e histogramas
    logging.py           # Formateador JSON que inyecta trace_id/span_id
load_generator.py        # Script de carga sintetica
docker-compose.yml       # Para correr conectado al stack LGTM
Dockerfile               # Multi-stage
```

## Licencia

MIT
