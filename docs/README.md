<!-- Creado por Aldo Garcia. -->

# docs/

Documentación técnica de Matrix RH.

| Documento | Contenido |
|---|---|
| `ARCHITECTURE.md` | Componentes runtime, flujos y decisiones |
| `AI_DESIGN.md` | Agentes, política de los dos modelos, anti-alucinación |
| `RAG_DESIGN.md` | Parámetros del RAG y dónde vive cada uno en el código |
| `DATA_MODEL.md` | Modelo de datos interno |
| `AUTHENTICATION_AUTHORIZATION.md` | Identidad, sesiones, RBAC, matriz de permisos |
| `ACCESS_PROFILES.md` | Perfiles HCM acumulativos, mínimo privilegio y segregación de Nómina |
| `DOCUMENTATION_GOVERNANCE.md` | Estructura oficial `general`/`especializadas`, publicación y resumen de adjuntos |
| `OPERATOR_QUICKSTART.md` | Instalación, inicio, diagnóstico y operación mínima en Windows |
| `SECURITY.md` | Controles implementados |
| `THREAT_MODEL.md` | Modelo de amenazas STRIDE + LLM/RAG |
| `TESTING.md` | Estrategia de pruebas |
| `E2E.md` | Flujos críticos end-to-end |
| `DEPLOYMENT.md` | Despliegue y contenerización |
| `DEPLOYMENT_V2.md` | Instalación portable, actualización de datos y aceptación en servidor nuevo |
| `MODEL_PROVIDERS.md` | Configuración única de modelos y adapters locales/Vertex opcional |
| `LOCAL_FINETUNING.md` | Comparación local y decisión RAG frente a fine-tuning |
| `FINAL_CONSOLIDATION.md` | Comparación GitHub 1.1.0 → revisión 1.2.0 → consolidación 1.2.1 |
| `RUNBOOK.md` | Operación diaria |
| `TROUBLESHOOTING.md` | Errores comunes y recuperación |
| `EXTERNAL_DEPENDENCIES_STATUS.md` | Estado real de cada integración |
| `REQUIREMENTS_TRACEABILITY.md` | Requisito → componente → prueba → evidencia |
| `FINAL_AUDIT.md` | Auditoría final |
| `integrations/` | Guías de conexión externa |

Las guías operativas describen el sistema **tal como está implementado**, con
referencias al archivo y la clase concretos. `FINAL_AUDIT.md` y los informes
versionados de `reports/` se conservan como evidencia histórica de su fecha de
corte; no acreditan pruebas de una entrega posterior.
