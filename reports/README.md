<!-- Creado por Aldo Garcia. -->

# reports/

Se versionan los informes narrativos Markdown revisados. Los resultados crudos
JSON/XML y logs no se incluyen en la entrega: pueden contener rutas, estadísticas
o datos del equipo donde se ejecutaron. Cada informe declara su versión/alcance.

| Carpeta | Contenido |
|---|---|
| `agent_reviews/` | Revisión de cada agente del proceso de construcción |
| `tests/` | JUnit, cobertura, resultados de Playwright y del golden set |
| `security/` | Escaneo de secretos, SAST y revisión de ciberseguridad |
| `final-validation.json` | Resumen de `windows\Validate-MatrixRH.ps1` |

## Auditoría de arquitectura y modelos locales 1.2.2

[LOCAL_ARCHITECTURE_E2E_AUDIT.md](LOCAL_ARCHITECTURE_E2E_AUDIT.md) distingue
correcciones, reproducciones sintéticas, E2E pendiente y prioridades del servidor.

## Instalación y modelos locales 1.2.3

[LOCAL_MODEL_READINESS_1.2.3.md](LOCAL_MODEL_READINESS_1.2.3.md) registra la
validación integrada, modelos futuros, embedding conservado y pruebas pendientes.
[SUPPLY_CHAIN_1.2.3.md](SUPPLY_CHAIN_1.2.3.md) detalla la instalación limpia,
las auditorías npm y los gates de instalación corregidos.
