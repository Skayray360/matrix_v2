# Estrategia de pruebas — Matrix RH

> Creado por Aldo Garcia.

---

## 1. Pirámide

| Suite | Ubicación | Requiere | Qué cubre |
|---|---|---|---|
| Unitarias | `backend/tests/unit/` | nada | Configuración, política de modelos, identidad/general/documental, resumen largo y ACL privada, perfiles HCM, taxonomía, alcance admin, chunking, grounding, SQL, memoria y mensajes al operador |
| Integración | `backend/tests/integration/` | MySQL | Esquema vs ORM, migraciones idempotentes, seed, API + sesión + CSRF + ownership, **propiedad y adopción de la base de datos** |
| Seguridad | `backend/tests/security/` | MySQL | Auth bypass, escalada de rol, IDOR/BOLA, SQLi, uploads maliciosos, rate limiting, secretos en respuestas, cabeceras |
| Golden set RAG | `backend/tests/rag_eval/` | Qdrant + Ollama | Recuperación, corrección de fuente, insuficiencia y **fuga ACL** |
| Componentes frontend | `frontend/tests/` | Node | Markdown seguro (XSS), composer, estados |
| E2E Playwright | `frontend/tests/e2e/` | Pila completa arriba | 28 pruebas recopiladas en 4 specs; varias agrupan más de un flujo |

Las pruebas unitarias **no** requieren MySQL, Qdrant ni Ollama. Las de
integración se **saltan** explícitamente (`skip`) cuando falta la dependencia, en
lugar de fallar y contaminar el porcentaje de aprobación.

Una omisión indica **no evaluado**, nunca una aprobación. La suite de integración
incluye fixtures con `DELETE` y `COMMIT`; use una copia dedicada, sin datos reales,
con `APP_ENV=test`, base `matrix_rh_test` (o `matrix_rh_test_<sufijo>`),
`MATRIX_TEST_ALLOW_DESTRUCTIVE=true`, `QDRANT_PATH=./var/tests/qdrant` y
`UPLOAD_STORAGE_ROOT=./var/tests/uploads`. En Qdrant servidor, ambas colecciones
deben comenzar por `matrix_rh_test_`. La guardia bloquea antes de ejecutar fixtures
si hay una base disponible que no cumple estos requisitos. Nunca renombre una
base operativa para eludirla. El script Windows comprueba esta configuración
antes de detener servicios, migrar o ingerir.

La autorización destructiva se declara **en la terminal de pruebas**, no se
guarda en la configuración operativa. En `cmd.exe`, después de preparar la copia:

```bat
set "MATRIX_TEST_ALLOW_DESTRUCTIVE=true"
```

El resto de valores se configura en la copia de pruebas. La validación no cambia
automáticamente credenciales ni crea una copia de la base operativa.

Los validadores distinguen `PASS` (salida 0), `FAIL` (salida 1) e `INCOMPLETE`
(salida 2). Una suite obligatoria omitida, un JUnit de integración/seguridad con
casos omitidos o evaluar únicamente recuperación no certifica una entrega
completa. `-SkipE2E`, `-QuickRag` y el modo rápido siguen disponibles, con resultado
parcial explícito. Los informes incluyen los pasos pendientes.

---

## 2. Ejecución

Desde la raíz del proyecto en `cmd.exe`:

```bat
set "PYTHONPATH=%CD%\backend"
.venv\Scripts\python.exe -m pytest backend\tests\unit -q
```
```bat
set "PYTHONPATH=%CD%\backend"
.venv\Scripts\python.exe -m pytest backend\tests\integration backend\tests\security -q
```
```bat
set "PYTHONPATH=%CD%\backend"
.venv\Scripts\python.exe -m scripts.rag_eval --retrieval
```
```bat
cd frontend
corepack npm test
```
```bat
cd frontend
corepack npm run e2e
```

Todo junto, con evidencia:

```bash
powershell -ExecutionPolicy Bypass -File windows\Validate-MatrixRH.ps1
```

Quality gate coordinado:

```bat
set "PYTHONPATH=%CD%\backend"
.venv\Scripts\python.exe -m scripts.run_quality_gate
```

> **Orden obligatorio.** Con `QDRANT_MODE=embedded` el almacén admite un solo
> proceso. Las suites que acceden directamente al índice deben ejecutarse con el
> backend **detenido**; los E2E, con el backend **arriba**.
> `windows\Validate-MatrixRH.ps1` ya secuencia ambas fases.

---

## 3. Marcadores de pytest

| Marcador | Significado |
|---|---|
| `unit` | Pura, sin infraestructura |
| `integration` | Requiere MySQL/Qdrant/Ollama |
| `security` | Prueba de seguridad automatizada |
| `critical` | Gate crítico: no admite fallos |
| `ollama` | Requiere modelos reales |

---

## 4. Fixtures y datos

**Nunca se usa información real sensible.** Todo el corpus (`data/knowledge/`)
está marcado como sintético en el propio texto de cada documento. Los fixtures de
DOCX, XLSX y PDF se generan en memoria dentro de la prueba, de modo que no hay
binarios opacos en el repositorio.

Las cuentas `Matrix` y `MatrixR1` son credenciales sintéticas declaradas; el seed
es idempotente y está prohibido en producción.

---

## 5. Cobertura

Objetivo: **≥90 %** de líneas en el backend y **≥95 %** en los módulos críticos
de autorización y seguridad (`app/authorization/`, `app/auth/`, `app/security/`,
`app/structured_data/`).

Desde la raíz del proyecto:

```bat
set "PYTHONPATH=%CD%\backend"
.venv\Scripts\python.exe -m pytest backend\tests --cov=app --cov-report=term-missing
```

El reporte XML queda en `reports/tests/coverage.xml`.

---

## 6. Casos que existen a propósito

Además de los casos felices, la batería incluye deliberadamente:

- **Límite**: `chunk_size == overlap`, `fetch_k < top_k`, `IN` vacío, lista de un
  solo elemento, archivo de 0 bytes, PDF sin texto.
- **Negativo**: contraseña incorrecta, usuario inexistente, cookie falsificada,
  CSRF ausente, CSRF de otra sesión, conversación ajena, categoría no autorizada.
- **Errores deliberados**: DOCX corrupto, PDF corrupto, MIME spoofing, zip bomb,
  JSON inválido del planificador, plan con campo inventado.
- **Concurrencia**: lock de reconciliación tomado por otro proceso.
- **Regresión**: cada defecto encontrado durante la construcción dejó su prueba
  (ver `docs/REQUIREMENTS_TRACEABILITY.md`, sección de defectos).

Contratos nuevos de la 1.1.0:

| Contrato | Prueba principal |
|---|---|
| Identidad exacta sin LLM/RAG | `test_ai_runtime_contracts.py::TestIdentidadSinDependencias` |
| Separación general/documental RH | `test_ai_runtime_contracts.py::TestContratoDeIntencion` |
| Resumen sin embedding, ACL privada, límite y map/reduce | `test_ai_runtime_contracts.py` |
| Perfiles HCM acumulativos y Nómina segregada | `test_access_profile_contract.py` |
| Revocación Entra y base obligatoria | `test_entra_role_sync.py` |
| `general`/`especializadas` + compatibilidad legacy | `test_knowledge_layout.py` |
| Publicación y resumen admin dentro del alcance | `test_admin_category_scope.py` |

La revisión 1.2.0 añade `test_implementation_v2.py` para alcance de memoria,
generaciones, fallos de proveedores, configuración y schema. La consolidación
1.2.1 amplía regresiones de DOCX, contexto, grounding y contratos originales.
Los nombres y resultados realmente ejecutados están en
[FINAL_CONSOLIDATION_VALIDATION.md](../reports/FINAL_CONSOLIDATION_VALIDATION.md).
Los transportes controlados no evalúan un LLM real, y el build/Vitest no sustituyen
un navegador Windows, SSO empresarial o una carga de 250 usuarios.

`frontend/tests/E2EHelpers.test.ts` comprueba con dobles que el helper no acepta
respuestas antiguas, errores HTTP o mensajes de otra conversación; son pruebas
unitarias del harness y no se contabilizan como E2E ejecutados. Para revisar el
inventario sin iniciar navegador: `corepack npm run e2e -- --list` desde `frontend/`.

---

## 7. Reglas para quien añada pruebas

1. No alterar el código productivo para hacer pasar una prueba incorrecta.
2. Una prueba de seguridad que pasa por accidente es peor que ninguna: verificar
   que falla si se elimina el control.
3. Los fixtures deben ser reproducibles y sintéticos.
4. Si una prueba necesita relajar un control (por ejemplo, el rate limiter), debe
   **reiniciar el control**, no desactivarlo — y el control debe tener su propia
   prueba dedicada.
5. Los `skip` deben ser explícitos y por dependencia ausente, nunca por
   comodidad.

---

## 8. Criterios de aceptación

| Métrica | Umbral |
|---|---|
| Pass rate total | ≥ 98 % |
| E2E críticos | 100 % |
| Pruebas de seguridad críticas | 100 % |
| Aislamiento de autorización | 100 % |
| Secretos reales detectados | 0 |
| Vulnerabilidades Critical / High | 0 |
| Golden set RAG | ≥ 98 % |
| Fuga ACL | 0 % |
| Cobertura backend | ≥ 90 % |
| Cobertura módulos críticos | ≥ 95 % |
| Build/typecheck del frontend | sin errores |

## Evaluación de fuentes y modelos en 1.2.2

Actualización 1.2.3: la [sonda local explícita](MODEL_SMOKE_TEST.md) comprueba
inventario/revisión de embeddings, generación numérica y schema con los perfiles
configurados. Sin `--run-inference` no hace conexiones. Los tests de
`test_local_model_protocols_123.py`, `test_execution_profiles.py`,
`test_model_smoke_test.py` y `test_embedding_switch_contracts.py` usan respuestas
controladas; no sustituyen E2E con pesos reales ni la comparación
[EmbeddingGemma/E5](EMBEDDING_COMPARISON.md). Ver resultados actuales en
[el informe 1.2.3](../reports/LOCAL_MODEL_READINESS_1.2.3.md).

Los 22 casos grounded del golden set (36 casos totales) incluyen source_ids y
hechos contrastados con los documentos sintéticos. Las anotaciones corresponden
a fragmentación 900/120; otro perfil exige revisar fuentes antes de ejecutar.
`--retrieval` mide recuperación y ACL, dejando métricas de respuesta en null;
`--full` requiere la base descartable autorizada y los modelos reales. La tasa
de respuestas aprobadas sigue siendo un contrato sintético, no una medición
semántica universal. No usar grounded como sustituto de revisión factual.

`run_quality_gate` y `Validate-MatrixRH.ps1` distinguen PASS, FAIL e INCOMPLETE.
Omitir E2E, omitir casos obligatorios o evaluar solo recuperación impide anunciar
validación completa. INCOMPLETE devuelve código 2; FAIL devuelve 1.
