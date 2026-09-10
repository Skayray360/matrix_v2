# Comparación de archivos — Matrix RH 1.2.1

> Creado por Aldo Garcia. Fecha: 2026-09-10.

## Bases y criterio

- GitHub 1.1.0: `94fa083b59553df18040150b4b714ae25afa5cbc`.
- Revisión 1.2.0: `472607fb268ae2277f7d4de1be012998f6cc5663`.
- Consolidación: rama `release/consolidated-1.2.1`, contenida en `source-history.bundle`.

Se compararon los objetos Git de cada archivo con el contenido final. Conservado
significa bytes idénticos; Modificado conserva la ruta con contenido actualizado.
Los archivos añadidos mantienen las carpetas y convenciones existentes. Esta
tabla no incluye runtime, dependencias ni el build generado de la interfaz;
el manifiesto SHA256SUMS del ZIP sí permite verificar sus recursos distribuidos.

## Resultado

| Estado | GitHub → final | v1.2.0 → final |
|---|---:|---:|
| Conservado | 168 | 215 |
| Modificado | 104 | 79 |
| Añadido | 30 | 8 |
| Ausente | 0 | 0 |

Total fuente/documentación final: **302 archivos**. Base GitHub: **272**.

Ningún archivo original está ausente. Las migraciones 0001–0003, la configuración
de autorización y los estilos del frontend conservan sus bytes. Los cambios de
lógica se detallan por causa y corrección en el changelog del README.

## Inventario completo

| Archivo | GitHub → v1.2.0 | v1.2.0 → final | GitHub → final |
|---|---|---|---|
| `.dockerignore` | No existía | Añadido | Añadido |
| `.env.example` | Modificado | Conservado | Modificado |
| `.github/workflows/implementation-v2.yml` | Añadido | Modificado | Añadido |
| `.gitignore` | Conservado | Modificado | Modificado |
| `.htaccess` | Conservado | Conservado | Conservado |
| `CHANGELOG.md` | Conservado | Modificado | Modificado |
| `DETENER_MATRIX_RH.bat` | Conservado | Conservado | Conservado |
| `DIAGNOSTICO_MATRIX_RH.bat` | Conservado | Conservado | Conservado |
| `INICIAR_MATRIX_RH.bat` | Conservado | Conservado | Conservado |
| `INSTALAR_MATRIX_RH.bat` | Conservado | Conservado | Conservado |
| `README.md` | Modificado | Modificado | Modificado |
| `SECURITY.md` | Conservado | Conservado | Conservado |
| `backend/Dockerfile` | Conservado | Modificado | Modificado |
| `backend/README.md` | Conservado | Conservado | Conservado |
| `backend/app/README.md` | Conservado | Conservado | Conservado |
| `backend/app/__init__.py` | Modificado | Modificado | Modificado |
| `backend/app/agents/README.md` | Conservado | Conservado | Conservado |
| `backend/app/agents/__init__.py` | Conservado | Conservado | Conservado |
| `backend/app/agents/knowledge_agent.py` | Modificado | Modificado | Modificado |
| `backend/app/agents/orchestrator.py` | Modificado | Modificado | Modificado |
| `backend/app/agents/prompts.py` | Modificado | Modificado | Modificado |
| `backend/app/agents/query_planner.py` | Modificado | Conservado | Modificado |
| `backend/app/api/README.md` | Conservado | Conservado | Conservado |
| `backend/app/api/__init__.py` | Conservado | Conservado | Conservado |
| `backend/app/api/body_limit.py` | Añadido | Conservado | Añadido |
| `backend/app/api/deps.py` | Conservado | Conservado | Conservado |
| `backend/app/api/middleware.py` | Modificado | Conservado | Modificado |
| `backend/app/api/routes/__init__.py` | Conservado | Conservado | Conservado |
| `backend/app/api/routes/admin.py` | Modificado | Conservado | Modificado |
| `backend/app/api/routes/auth.py` | Modificado | Conservado | Modificado |
| `backend/app/api/routes/chat.py` | Modificado | Conservado | Modificado |
| `backend/app/api/routes/conversations.py` | Modificado | Conservado | Modificado |
| `backend/app/api/routes/health.py` | Modificado | Conservado | Modificado |
| `backend/app/api/schemas.py` | Modificado | Conservado | Modificado |
| `backend/app/audit/README.md` | Conservado | Conservado | Conservado |
| `backend/app/audit/__init__.py` | Conservado | Conservado | Conservado |
| `backend/app/audit/service.py` | Conservado | Conservado | Conservado |
| `backend/app/auth/README.md` | Modificado | Conservado | Modificado |
| `backend/app/auth/__init__.py` | Conservado | Conservado | Conservado |
| `backend/app/auth/entra_provider.py` | Modificado | Conservado | Modificado |
| `backend/app/auth/local_provider.py` | Conservado | Conservado | Conservado |
| `backend/app/auth/oidc_provider.py` | Añadido | Conservado | Añadido |
| `backend/app/auth/passwords.py` | Conservado | Conservado | Conservado |
| `backend/app/auth/provider.py` | Modificado | Conservado | Modificado |
| `backend/app/auth/sessions.py` | Conservado | Conservado | Conservado |
| `backend/app/authorization/README.md` | Conservado | Conservado | Conservado |
| `backend/app/authorization/__init__.py` | Conservado | Conservado | Conservado |
| `backend/app/authorization/categories.py` | Conservado | Conservado | Conservado |
| `backend/app/authorization/context.py` | Conservado | Conservado | Conservado |
| `backend/app/authorization/policy.py` | Conservado | Conservado | Conservado |
| `backend/app/common/README.md` | Conservado | Conservado | Conservado |
| `backend/app/common/__init__.py` | Conservado | Conservado | Conservado |
| `backend/app/common/errors.py` | Conservado | Conservado | Conservado |
| `backend/app/common/ids.py` | Conservado | Conservado | Conservado |
| `backend/app/common/logging.py` | Conservado | Conservado | Conservado |
| `backend/app/common/redaction.py` | Conservado | Conservado | Conservado |
| `backend/app/config/README.md` | Conservado | Modificado | Modificado |
| `backend/app/config/__init__.py` | Conservado | Conservado | Conservado |
| `backend/app/config/settings.py` | Modificado | Conservado | Modificado |
| `backend/app/database/README.md` | Conservado | Conservado | Conservado |
| `backend/app/database/__init__.py` | Conservado | Conservado | Conservado |
| `backend/app/database/engine.py` | Conservado | Conservado | Conservado |
| `backend/app/database/migrator.py` | Conservado | Modificado | Modificado |
| `backend/app/database/models.py` | Modificado | Conservado | Modificado |
| `backend/app/ingestion/README.md` | Conservado | Modificado | Modificado |
| `backend/app/ingestion/__init__.py` | Conservado | Conservado | Conservado |
| `backend/app/ingestion/extract_worker.py` | Añadido | Conservado | Añadido |
| `backend/app/ingestion/isolated_extraction.py` | Añadido | Modificado | Añadido |
| `backend/app/ingestion/loaders.py` | Conservado | Modificado | Modificado |
| `backend/app/ingestion/reconciler.py` | Modificado | Modificado | Modificado |
| `backend/app/ingestion/service.py` | Modificado | Modificado | Modificado |
| `backend/app/jobs/README.md` | Conservado | Conservado | Conservado |
| `backend/app/jobs/__init__.py` | Conservado | Conservado | Conservado |
| `backend/app/jobs/scheduler.py` | Conservado | Conservado | Conservado |
| `backend/app/llm/README.md` | Modificado | Conservado | Modificado |
| `backend/app/llm/__init__.py` | Conservado | Conservado | Conservado |
| `backend/app/llm/model_policy.py` | Modificado | Conservado | Modificado |
| `backend/app/llm/ollama_client.py` | Modificado | Modificado | Modificado |
| `backend/app/llm/provider.py` | Añadido | Modificado | Añadido |
| `backend/app/main.py` | Modificado | Conservado | Modificado |
| `backend/app/memory/README.md` | Conservado | Modificado | Modificado |
| `backend/app/memory/__init__.py` | Conservado | Conservado | Conservado |
| `backend/app/memory/service.py` | Modificado | Modificado | Modificado |
| `backend/app/rag/README.md` | Conservado | Modificado | Modificado |
| `backend/app/rag/__init__.py` | Conservado | Conservado | Conservado |
| `backend/app/rag/chunking.py` | Conservado | Conservado | Conservado |
| `backend/app/rag/embedding_prompts.py` | Modificado | Conservado | Modificado |
| `backend/app/rag/grounding.py` | Modificado | Modificado | Modificado |
| `backend/app/rag/index_manifest.py` | Añadido | Modificado | Añadido |
| `backend/app/rag/retriever.py` | Modificado | Modificado | Modificado |
| `backend/app/rag/schemas.py` | Modificado | Conservado | Modificado |
| `backend/app/rag/vector_store.py` | Modificado | Modificado | Modificado |
| `backend/app/security/README.md` | Conservado | Conservado | Conservado |
| `backend/app/security/__init__.py` | Conservado | Conservado | Conservado |
| `backend/app/security/admission.py` | Añadido | Conservado | Añadido |
| `backend/app/security/prompt_guard.py` | Conservado | Conservado | Conservado |
| `backend/app/security/rate_limit.py` | Conservado | Conservado | Conservado |
| `backend/app/security/upload_guard.py` | Modificado | Conservado | Modificado |
| `backend/app/structured_data/README.md` | Conservado | Conservado | Conservado |
| `backend/app/structured_data/__init__.py` | Conservado | Conservado | Conservado |
| `backend/app/structured_data/adapters.py` | Modificado | Conservado | Modificado |
| `backend/app/structured_data/compiler.py` | Conservado | Conservado | Conservado |
| `backend/app/structured_data/schemas.py` | Conservado | Modificado | Modificado |
| `backend/app/structured_data/sources.py` | Conservado | Conservado | Conservado |
| `backend/app/structured_data/tool.py` | Conservado | Conservado | Conservado |
| `backend/app/structured_data/validator.py` | Conservado | Conservado | Conservado |
| `backend/migrations/0001_initial_schema.sql` | Conservado | Conservado | Conservado |
| `backend/migrations/0002_widen_audit_status.sql` | Conservado | Conservado | Conservado |
| `backend/migrations/0003_message_sequence.sql` | Conservado | Conservado | Conservado |
| `backend/migrations/0004_memory_authorization.sql` | Añadido | Conservado | Añadido |
| `backend/migrations/0005_index_generations.sql` | Añadido | Conservado | Añadido |
| `backend/migrations/0006_chat_operations.sql` | Añadido | Conservado | Añadido |
| `backend/migrations/README.md` | Conservado | Conservado | Conservado |
| `backend/pyproject.toml` | Modificado | Modificado | Modificado |
| `backend/scripts/README.md` | Conservado | Conservado | Conservado |
| `backend/scripts/__init__.py` | Conservado | Conservado | Conservado |
| `backend/scripts/bootstrap.py` | Modificado | Conservado | Modificado |
| `backend/scripts/load_entra_mapping.py` | Conservado | Conservado | Conservado |
| `backend/scripts/load_test.py` | Añadido | Conservado | Añadido |
| `backend/scripts/model_inventory.py` | Añadido | Conservado | Añadido |
| `backend/scripts/package_release.py` | Modificado | Modificado | Modificado |
| `backend/scripts/preflight.py` | Modificado | Modificado | Modificado |
| `backend/scripts/rag_eval.py` | Modificado | Conservado | Modificado |
| `backend/scripts/run_quality_gate.py` | Modificado | Modificado | Modificado |
| `backend/scripts/secrets_scan.py` | Conservado | Conservado | Conservado |
| `backend/scripts/smoke_authorization.py` | Conservado | Conservado | Conservado |
| `backend/scripts/verify_headers.py` | Conservado | Modificado | Modificado |
| `backend/scripts/verify_supply_chain.py` | Modificado | Modificado | Modificado |
| `backend/seeds/README.md` | Conservado | Conservado | Conservado |
| `backend/seeds/__init__.py` | Conservado | Conservado | Conservado |
| `backend/seeds/identity_seed.py` | Conservado | Conservado | Conservado |
| `backend/tests/README.md` | Conservado | Conservado | Conservado |
| `backend/tests/__init__.py` | Conservado | Conservado | Conservado |
| `backend/tests/conftest.py` | Conservado | Conservado | Conservado |
| `backend/tests/integration/test_api_auth.py` | Conservado | Conservado | Conservado |
| `backend/tests/integration/test_database_adoption.py` | Conservado | Conservado | Conservado |
| `backend/tests/integration/test_database_ownership.py` | Conservado | Modificado | Modificado |
| `backend/tests/integration/test_entra_flow_mock.py` | Conservado | Conservado | Conservado |
| `backend/tests/integration/test_ingestion_and_memory.py` | Conservado | Conservado | Conservado |
| `backend/tests/integration/test_reconciler.py` | Conservado | Conservado | Conservado |
| `backend/tests/integration/test_schema_and_seed.py` | Conservado | Conservado | Conservado |
| `backend/tests/integration/test_sessions_and_migrations.py` | Conservado | Conservado | Conservado |
| `backend/tests/integration/test_structured_end_to_end.py` | Conservado | Conservado | Conservado |
| `backend/tests/rag_eval/golden_set.yaml` | Conservado | Conservado | Conservado |
| `backend/tests/security/test_attack_surface.py` | Conservado | Conservado | Conservado |
| `backend/tests/security/test_release_runtime_contract.py` | Modificado | Conservado | Modificado |
| `backend/tests/security/test_supply_chain.py` | Modificado | Modificado | Modificado |
| `backend/tests/unit/conftest.py` | Añadido | Conservado | Añadido |
| `backend/tests/unit/test_access_profile_contract.py` | Conservado | Conservado | Conservado |
| `backend/tests/unit/test_admin_category_scope.py` | Conservado | Conservado | Conservado |
| `backend/tests/unit/test_ai_runtime_contracts.py` | Modificado | Modificado | Modificado |
| `backend/tests/unit/test_authorization.py` | Conservado | Conservado | Conservado |
| `backend/tests/unit/test_backend_consolidation.py` | No existía | Añadido | Añadido |
| `backend/tests/unit/test_chunking.py` | Conservado | Conservado | Conservado |
| `backend/tests/unit/test_config.py` | Modificado | Conservado | Modificado |
| `backend/tests/unit/test_coverage_gaps.py` | Conservado | Conservado | Conservado |
| `backend/tests/unit/test_critical_module_branches.py` | Modificado | Conservado | Modificado |
| `backend/tests/unit/test_entra_role_sync.py` | Conservado | Conservado | Conservado |
| `backend/tests/unit/test_grounding.py` | Modificado | Modificado | Modificado |
| `backend/tests/unit/test_identity_and_policy_edges.py` | Modificado | Conservado | Modificado |
| `backend/tests/unit/test_implementation_v2.py` | Añadido | Modificado | Añadido |
| `backend/tests/unit/test_installer_consolidation.py` | No existía | Añadido | Añadido |
| `backend/tests/unit/test_knowledge_layout.py` | Conservado | Conservado | Conservado |
| `backend/tests/unit/test_llm_client.py` | Modificado | Conservado | Modificado |
| `backend/tests/unit/test_loaders.py` | Conservado | Conservado | Conservado |
| `backend/tests/unit/test_memory_and_agent.py` | Conservado | Modificado | Modificado |
| `backend/tests/unit/test_model_policy.py` | Conservado | Conservado | Conservado |
| `backend/tests/unit/test_operator_messages.py` | Conservado | Conservado | Conservado |
| `backend/tests/unit/test_private_reindex_final.py` | No existía | Añadido | Añadido |
| `backend/tests/unit/test_rag_integrity_final.py` | No existía | Añadido | Añadido |
| `backend/tests/unit/test_rag_pipeline_isolated.py` | Modificado | Conservado | Modificado |
| `backend/tests/unit/test_retrieval_ranking.py` | Conservado | Conservado | Conservado |
| `backend/tests/unit/test_security_controls.py` | Conservado | Conservado | Conservado |
| `backend/tests/unit/test_services_isolated.py` | Conservado | Conservado | Conservado |
| `backend/tests/unit/test_structured_query.py` | Conservado | Conservado | Conservado |
| `backend/uv.lock` | Modificado | Modificado | Modificado |
| `config/README.md` | Conservado | Conservado | Conservado |
| `config/authorization/README.md` | Conservado | Conservado | Conservado |
| `config/authorization/categories.yaml` | Conservado | Conservado | Conservado |
| `config/authorization/entra-role-mapping.yaml` | Conservado | Conservado | Conservado |
| `config/data_sources/README.md` | Conservado | Conservado | Conservado |
| `config/data_sources/sources.yaml` | Conservado | Conservado | Conservado |
| `config/supply_chain_denylist.yaml` | Conservado | Conservado | Conservado |
| `data/README.md` | Conservado | Conservado | Conservado |
| `data/knowledge/README.md` | Conservado | Conservado | Conservado |
| `data/knowledge/especializadas/README.md` | Conservado | Conservado | Conservado |
| `data/knowledge/especializadas/administracion_personal/README.md` | Conservado | Conservado | Conservado |
| `data/knowledge/especializadas/capacitacion/README.md` | Conservado | Conservado | Conservado |
| `data/knowledge/especializadas/compensaciones/README.md` | Conservado | Conservado | Conservado |
| `data/knowledge/especializadas/documentacion_empresarial/README.md` | Conservado | Conservado | Conservado |
| `data/knowledge/especializadas/matrix_rh_ia/README.md` | Conservado | Conservado | Conservado |
| `data/knowledge/especializadas/nomina_confidencial/README.md` | Conservado | Conservado | Conservado |
| `data/knowledge/especializadas/nomina_general/README.md` | Conservado | Conservado | Conservado |
| `data/knowledge/especializadas/reclutamiento/README.md` | Conservado | Conservado | Conservado |
| `data/knowledge/especializadas/relaciones_laborales/README.md` | Conservado | Conservado | Conservado |
| `data/knowledge/especializadas/talento/README.md` | Conservado | Conservado | Conservado |
| `data/knowledge/general/README.md` | Conservado | Conservado | Conservado |
| `data/knowledge/nomina/README.md` | Conservado | Conservado | Conservado |
| `data/knowledge/nomina/politica-de-nomina.md` | Conservado | Conservado | Conservado |
| `data/knowledge/prestaciones/README.md` | Conservado | Conservado | Conservado |
| `data/knowledge/prestaciones/fondo-de-ahorro-y-aguinaldo.md` | Conservado | Conservado | Conservado |
| `data/knowledge/prestaciones/politica-vacaciones.md` | Conservado | Conservado | Conservado |
| `data/knowledge/reclutamiento/README.md` | Conservado | Conservado | Conservado |
| `data/knowledge/reclutamiento/proceso-de-reclutamiento.md` | Conservado | Conservado | Conservado |
| `data/knowledge/relaciones_laborales/README.md` | Conservado | Conservado | Conservado |
| `data/knowledge/relaciones_laborales/reglamento-interior.md` | Conservado | Conservado | Conservado |
| `data/knowledge/salud_ambiental/README.md` | Conservado | Conservado | Conservado |
| `data/knowledge/salud_ambiental/seguridad-higiene-y-ambiente.md` | Conservado | Conservado | Conservado |
| `data/synthetic_test_data/README.md` | Conservado | Conservado | Conservado |
| `docker-compose.yml` | Modificado | Modificado | Modificado |
| `docs/ACCESS_PROFILES.md` | Conservado | Conservado | Conservado |
| `docs/AI_DESIGN.md` | Conservado | Modificado | Modificado |
| `docs/ARCHITECTURE.md` | Conservado | Modificado | Modificado |
| `docs/AUTHENTICATION_AUTHORIZATION.md` | Modificado | Conservado | Modificado |
| `docs/DATA_MODEL.md` | Conservado | Modificado | Modificado |
| `docs/DEPLOYMENT.md` | Modificado | Modificado | Modificado |
| `docs/DEPLOYMENT_V2.md` | Añadido | Modificado | Añadido |
| `docs/DOCUMENTATION_GOVERNANCE.md` | Conservado | Conservado | Conservado |
| `docs/E2E.md` | Conservado | Conservado | Conservado |
| `docs/EXTERNAL_DEPENDENCIES_STATUS.md` | Conservado | Modificado | Modificado |
| `docs/FINAL_AUDIT.md` | Conservado | Modificado | Modificado |
| `docs/FINAL_CONSOLIDATION.md` | No existía | Añadido | Añadido |
| `docs/LOCAL_FINETUNING.md` | Añadido | Conservado | Añadido |
| `docs/MODEL_PROVIDERS.md` | Añadido | Modificado | Añadido |
| `docs/OPERATOR_QUICKSTART.md` | Modificado | Modificado | Modificado |
| `docs/RAG_DESIGN.md` | Conservado | Modificado | Modificado |
| `docs/README.md` | Conservado | Modificado | Modificado |
| `docs/REQUIREMENTS_TRACEABILITY.md` | Conservado | Modificado | Modificado |
| `docs/RUNBOOK.md` | Conservado | Conservado | Conservado |
| `docs/SECURITY.md` | Conservado | Modificado | Modificado |
| `docs/TESTING.md` | Conservado | Modificado | Modificado |
| `docs/THREAT_MODEL.md` | Conservado | Modificado | Modificado |
| `docs/TROUBLESHOOTING.md` | Conservado | Conservado | Conservado |
| `docs/integrations/AD_ACTIVATION_CHECKLIST.md` | Añadido | Modificado | Añadido |
| `docs/integrations/DATABASE_CONNECTORS.md` | Conservado | Conservado | Conservado |
| `docs/integrations/ENTRA_ID_SETUP.md` | Modificado | Conservado | Modificado |
| `docs/integrations/IDENTITY_PROVIDER_DESIGN.md` | Conservado | Modificado | Modificado |
| `docs/integrations/MIGRATE_LOCAL_TEST_TO_ENTRA.md` | Conservado | Conservado | Conservado |
| `docs/integrations/README.md` | Conservado | Modificado | Modificado |
| `frontend/.npmrc` | Conservado | Modificado | Modificado |
| `frontend/README.md` | Modificado | Modificado | Modificado |
| `frontend/index.html` | Conservado | Conservado | Conservado |
| `frontend/package-lock.json` | Modificado | Modificado | Modificado |
| `frontend/package.json` | Modificado | Modificado | Modificado |
| `frontend/playwright.config.ts` | Conservado | Conservado | Conservado |
| `frontend/src/App.tsx` | Conservado | Conservado | Conservado |
| `frontend/src/README.md` | Conservado | Conservado | Conservado |
| `frontend/src/components/Composer.tsx` | Modificado | Conservado | Modificado |
| `frontend/src/components/Icon.tsx` | Conservado | Conservado | Conservado |
| `frontend/src/components/MessageList.tsx` | Conservado | Modificado | Modificado |
| `frontend/src/components/QuickActions.tsx` | Conservado | Conservado | Conservado |
| `frontend/src/components/README.md` | Conservado | Conservado | Conservado |
| `frontend/src/components/Sidebar.tsx` | Modificado | Modificado | Modificado |
| `frontend/src/components/ThemeControl.tsx` | Conservado | Conservado | Conservado |
| `frontend/src/components/TracePanel.tsx` | Conservado | Modificado | Modificado |
| `frontend/src/main.tsx` | Conservado | Conservado | Conservado |
| `frontend/src/pages/ChatPage.tsx` | Modificado | Modificado | Modificado |
| `frontend/src/pages/LoginPage.tsx` | Modificado | Modificado | Modificado |
| `frontend/src/pages/README.md` | Conservado | Conservado | Conservado |
| `frontend/src/security/Markdown.tsx` | Conservado | Conservado | Conservado |
| `frontend/src/security/README.md` | Conservado | Conservado | Conservado |
| `frontend/src/services/README.md` | Conservado | Conservado | Conservado |
| `frontend/src/services/api.ts` | Modificado | Conservado | Modificado |
| `frontend/src/styles.css` | Conservado | Conservado | Conservado |
| `frontend/tests/ChatPage.test.tsx` | Añadido | Modificado | Añadido |
| `frontend/tests/Composer.test.tsx` | Conservado | Modificado | Modificado |
| `frontend/tests/Markdown.test.tsx` | Conservado | Conservado | Conservado |
| `frontend/tests/QuickActions.test.tsx` | Conservado | Conservado | Conservado |
| `frontend/tests/README.md` | Conservado | Modificado | Modificado |
| `frontend/tests/TracePanel.test.tsx` | Conservado | Modificado | Modificado |
| `frontend/tests/e2e/01-auth.spec.ts` | Conservado | Conservado | Conservado |
| `frontend/tests/e2e/02-authorization.spec.ts` | Conservado | Conservado | Conservado |
| `frontend/tests/e2e/03-documents-memory.spec.ts` | Conservado | Conservado | Conservado |
| `frontend/tests/e2e/04-operations.spec.ts` | Conservado | Conservado | Conservado |
| `frontend/tests/e2e/README.md` | Conservado | Modificado | Modificado |
| `frontend/tests/e2e/helpers.ts` | Conservado | Conservado | Conservado |
| `frontend/tests/setup.ts` | Conservado | Conservado | Conservado |
| `frontend/tsconfig.json` | Conservado | Conservado | Conservado |
| `frontend/vite.config.ts` | Conservado | Conservado | Conservado |
| `infrastructure/README.md` | Conservado | Conservado | Conservado |
| `infrastructure/database/README.md` | Conservado | Conservado | Conservado |
| `infrastructure/database/init/01-create-database.sql` | Conservado | Conservado | Conservado |
| `infrastructure/database/init/README.md` | Conservado | Conservado | Conservado |
| `infrastructure/nginx/README.md` | Conservado | Conservado | Conservado |
| `infrastructure/nginx/matrixrh.conf` | Conservado | Conservado | Conservado |
| `infrastructure/qdrant/README.md` | Conservado | Conservado | Conservado |
| `install.bat` | Añadido | Conservado | Añadido |
| `reports/FINAL_CONSOLIDATION_VALIDATION.md` | No existía | Añadido | Añadido |
| `reports/FINAL_SOURCE_COMPARISON.md` | No existía | Añadido | Añadido |
| `reports/IMPLEMENTATION_V2_VALIDATION.md` | Añadido | Conservado | Añadido |
| `reports/README.md` | Conservado | Conservado | Conservado |
| `reports/RELEASE_VALIDATION_1.1.0.md` | Conservado | Conservado | Conservado |
| `scripts/README.md` | Conservado | Modificado | Modificado |
| `scripts/matrixrh.sh` | Conservado | Modificado | Modificado |
| `windows/Common-MatrixRH.ps1` | Modificado | Modificado | Modificado |
| `windows/Diagnose-MatrixRH.ps1` | Conservado | Conservado | Conservado |
| `windows/Install-Autostart.ps1` | Conservado | Conservado | Conservado |
| `windows/Install-MatrixRH.ps1` | Modificado | Modificado | Modificado |
| `windows/README.md` | Conservado | Modificado | Modificado |
| `windows/Start-MatrixRH.ps1` | Modificado | Modificado | Modificado |
| `windows/Stop-MatrixRH.ps1` | Modificado | Conservado | Modificado |
| `windows/Validate-MatrixRH.ps1` | Modificado | Modificado | Modificado |

## Reproducción

Después de clonar `source-history.bundle`, ejecute:

```bash
git diff --stat 94fa083 release/consolidated-1.2.1
git diff --name-status 472607f release/consolidated-1.2.1
git diff 94fa083 release/consolidated-1.2.1 -- backend/migrations/0001_initial_schema.sql backend/migrations/0002_widen_audit_status.sql backend/migrations/0003_message_sequence.sql config/authorization
```

La última comparación sólo puede incluir cambios de documentación bajo
`config/authorization`; los archivos de políticas y las tres migraciones no
cambian.
