# Evidencia de implementación — Matrix RH 1.2.0

> Creado por Aldo Garcia. Fecha: 2026-09-09.
> Base auditada: `94fa083b59553df18040150b4b714ae25afa5cbc`.
> **Entrega para revisión; no aprobar capacidad ni despliegue empresarial todavía.**

## Alcance real

Se conservaron carpetas, adapters AD/Entra y nombres públicos existentes. El
README incluye el changelog de cada componente corregido en la misma entrega.
La configuración predeterminada sigue en modo de prueba local. No se activaron
AD, Entra, Vertex ni servicios externos del usuario.

| Requisito | Entrega | Límite de aceptación |
|---|---|---|
| R1 AD | Flag real, OIDC local adicional, seguridad del callback, checklist y corrección de documentación Entra | Login y revocación en AD/IdP real pendientes de TI |
| R2 modelos | Interface/adapters, parámetros en `.env`, contrato schema y prueba de cambio por archivo | Calidad/capacidad del nuevo modelo y Vertex real sin medir; módulo avanzado mencionado no existe en el commit base |
| R3 entrenamiento | Unsloth como framework elegido; comparación con Axolotl/LLaMA-Factory y separación de Modelfile | No iniciar entrenamiento sin dataset, inventario y mejora medida frente al RAG |
| R4 bugs | Correcciones de autorización, SQL, RAG, clientes, UI y dependencias, con migraciones y changelog | Revisión y aceptación de integración pendientes; el control de admisión es por proceso, no cola distribuida |
| R5 portabilidad | `install.bat`, instalador por config, lock real npm, venv trasladado, fallos propagados, checklist | No ejecutado de punta a punta sobre un servidor Windows nuevo con sus servicios reales |

## Ejecución local registrada

Entorno de revisión: Linux, Python 3.12.14, uv 0.12.8. Sin servidor Windows,
GPU/modelos Matrix, AD/Entra ni motores empresariales disponibles.

| Verificación | Resultado observado |
|---|---|
| `pytest backend/tests/unit backend/tests/security --tb=short` | **495 aprobadas, 37 omitidas, 1 fallida**; 533 casos |
| Fallo restante | `test_release_contiene_build_frontend_y_denegacion_wamp`: exige `frontend/dist/index.html`, ausente en el checkout fuente |
| Nuevas regresiones v2 | Cambio `.env` Ollama/API compatible; schema Vertex/JSON; bloqueo cloud; embeddings; 503 sin amplificación; admisión; ACL/historial/resumen; índice antes de commit; extracción aislada; cookie OIDC; conexión SQL liberada; idempotencia y revocación durante respuesta; solicitud expirada |
| `uv lock` y `uv sync --frozen --extra dev --offline` | Lock actualizado y paquete 1.2.0 sincronizado |
| `pip-audit` sobre entorno instalado | **0 avisos conocidos en 95 dependencias auditables**; paquete privado Matrix omitido por no existir en PyPI, revisado como código |
| Instalación frontend en este entorno | Bloqueada por autorización de red cancelada; el intento offline tampoco pudo completarse. No se fabricó un build para pasar el test |
| Typecheck/build/Vitest | No ejecutados; CI también bloqueado por la escritura GitHub rechazada |
| Ruff sobre app/scripts nuevos/regresiones v2 | Aprobado |
| Encabezados y escaneo de secretos | Aprobados; la credencial MySQL de CI es un fixture sintético explícito |
| Prueba de carga 200/250 | No ejecutada; herramienta y protocolo entregados, no resultados simulados |

Dependencias principales comprobadas: FastAPI 0.141.1, Starlette 1.6.0,
cryptography 50.0.1, PyJWT 2.13.0, pypdf 6.18.0 y python-multipart 0.0.32.
Cero avisos en un catálogo no demuestra ausencia de vulnerabilidades. El test
client emite una advertencia de deprecación httpx/httpx2; las pruebas ejecutadas
siguen funcionando. No se modifica ese test stack sin necesidad para ocultarla.

## Controles CI preparados

`.github/workflows/implementation-v2.yml` define:

1. Instalación fijada, build y Vitest del frontend, luego unitarias/seguridad del
   backend con el build real disponible.
2. Parser de PowerShell en Windows y prueba de `install.bat` en ruta con espacios,
   argumentos y propagación de exit code usando un delegado sintético. **No es
   una prueba integral de instalar Ollama/MySQL ni del servidor final.**
3. MySQL 8 aislado con datos sintéticos: migraciones, seed y contratos SQL/OIDC
   con tokens RSA firmados localmente.

Estado: **no ejecutados**. GitHub rechazó crear el árbol de cambios con HTTP 403
`Resource not accessible by integration` (`POST /repos/Skayray360/matrix/git/trees`).
Aunque la cuenta aparece con push/admin en los metadatos, la integración no
permitió esta escritura. No se publicó rama ni PR; el commit y parche se
entregan localmente para revisión. No se intentó eludir esa restricción. CI no recibe documentos, credenciales ni sesiones
empresariales. La operación del producto local no depende de GitHub Actions.

## Pendientes concretos antes de aceptar producción

- Compilación/pruebas de interfaz y contratos Windows/MySQL de CI aprobados.
- Instalación completa, reinicio y recuperación en Windows destino; servicios,
  CA, modelos y datos migrados explícitamente.
- Perfil productivo de autenticación configurado y aceptación TI. Entra cloud
  preservado; AD local requiere IdP interno instalado y federado.
- Qdrant servidor interno e ingesta completa de generaciones/huellas v4. No
  reutilizar silenciosamente índices sin fingerprint.
- Inventario de hardware, digests, cuantización y contexto; SLO definidos y
  mediciones reales 200 sostenidos/250 pico/recuperación.
- Cola durable y coordinación compartida si se requieren varios procesos API.
  Rechazar sobrecarga estabiliza recursos, pero no satisface por sí solo 250
  solicitudes admitidas a la vez.
- Calibración de exactitud factual y recuperación con corpus empresarial. El
  verificador conservador rechaza paráfrasis cuyo soporte no puede demostrar.
- Mantenimiento de puntos huérfanos invisibles tras fallos precommit y política
  de retención de operaciones idempotentes/adjuntos conforme a TI.
- El empaquetador conserva el gate de integridad del gestor de paquetes. Con
  `packageManager=npm@10.9.0` sin hash no se declara un ZIP aprobado; esta entrega
  es una rama de código, no un paquete instalable certificado.

Los informes 1.1.0 se preservan como históricos. No utilizar sus porcentajes o
la prueba sintética del adapter como certificación del servidor o de Gemini.
