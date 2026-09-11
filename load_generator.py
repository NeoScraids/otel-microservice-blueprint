"""
Generador de trafico y carga sintetica para poblar graficas en Grafana y trazas en Tempo.
"""

import time
import random
import sys
import httpx

TARGET_URL = "http://localhost:8080"


def generate_traffic(iterations: int = 50, delay: float = 0.5):
    print("=" * 70)
    print(f"  GENERADOR DE CARGA DE OBSERVABILIDAD")
    print(f"  Objetivo: {TARGET_URL} | Iteraciones: {iterations} | Pausa: {delay}s")
    print("=" * 70)

    success_count = 0
    error_count = 0

    with httpx.Client(base_url=TARGET_URL, timeout=10.0) as client:
        # Verificar salud inicial
        try:
            res = client.get("/health")
            print(f"Conexion establecida. Estado del servicio: {res.json()['status']}\n")
        except Exception as e:
            print(f"No se pudo conectar a {TARGET_URL}: {str(e)}")
            print("Asegurate de iniciar primero el microservicio con 'uvicorn src.main:app --port 8080'")
            sys.exit(1)

        for i in range(1, iterations + 1):
            rnd = random.random()
            try:
                if rnd < 0.65:
                    # Crear orden exitosa
                    order_data = {
                        "customer_id": f"cust_{random.randint(100, 999)}",
                        "items_count": random.randint(1, 10),
                        "amount": round(random.uniform(15.0, 350.0), 2)
                    }
                    r = client.post("/api/v1/orders", json=order_data)
                    print(f"[{i:03d}/{iterations:03d}] POST /api/v1/orders - Estado {r.status_code} ({r.elapsed.total_seconds():.3f}s)")
                    success_count += 1

                elif rnd < 0.85:
                    # Listar ordenes
                    r = client.get("/api/v1/orders")
                    print(f"[{i:03d}/{iterations:03d}] GET  /api/v1/orders - Estado {r.status_code} ({r.elapsed.total_seconds():.3f}s)")
                    success_count += 1

                elif rnd < 0.95:
                    # Simular operacion lenta
                    r = client.get("/simulate/slow")
                    print(f"[{i:03d}/{iterations:03d}] GET  /simulate/slow - Estado {r.status_code} (Latencia prolongada: {r.elapsed.total_seconds():.3f}s)")
                    success_count += 1

                else:
                    # Simular error 500
                    r = client.get("/simulate/error")
                    print(f"[{i:03d}/{iterations:03d}] GET  /simulate/error - Estado {r.status_code} (Error intencional provocado)")
                    error_count += 1

            except Exception as exc:
                print(f"[{i:03d}/{iterations:03d}] Fallo de solicitud: {str(exc)}")
                error_count += 1

            time.sleep(delay)

    print("\n" + "=" * 70)
    print(f"  RESUMEN DE CARGA GENERADA")
    print(f"  Exitosas: {success_count} | Errores / Excepciones: {error_count}")
    print("=" * 70)


if __name__ == "__main__":
    count = 30
    if len(sys.argv) > 1:
        try:
            count = int(sys.argv[1])
        except ValueError:
            pass
    generate_traffic(iterations=count)
