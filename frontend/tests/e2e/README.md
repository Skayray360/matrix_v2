<!-- Creado por Aldo Garcia. -->

# frontend/tests/e2e/

Pruebas Playwright de los flujos completos contra FastAPI sirviendo el frontend
compilado en el mismo origen.

Inventario actual: **28 pruebas en 4 specs**. `--list` solo recopila; no demuestra
que la pila ni los modelos hayan pasado las pruebas.

- Entradas: backend listo, corpus indexado y cuentas sintéticas de desarrollo.
- Salidas: resultados JSON, reporte HTML, trazas y capturas bajo las rutas
  configuradas en `playwright.config.ts`.
- Dependencias: árbol reproducible instalado con
  `corepack npm ci --ignore-scripts` y navegador
  instalado con `corepack npm run e2e:install`.

Ejecución desde `frontend/`:

```bat
corepack npm run e2e
```

El helper de chat correlaciona el POST exitoso, la conversación y el ID del nuevo
mensaje renderizado. Un mensaje anterior o un error no satisfacen la espera.
Las regresiones con dobles viven en `../E2EHelpers.test.ts` y son unitarias.
La prueba de routing toma los modelos efectivos de diagnóstico y exige el evento
con el `X-Request-ID` del chat actual; permite cambiar de modelo desde configuración.
Los parámetros del RAG se verifican por sus invariantes, sin fijar valores de tuning.

Use exclusivamente una instalación de pruebas con datos sintéticos. Antes de
ejecutar el validador completo, siga la separación de BD, índice y adjuntos de
[`../../../docs/TESTING.md`](../../../docs/TESTING.md).

Los helpers centralizan autenticación y aserciones de no fuga. Ningún spec debe
desactivar autorización para hacer pasar un escenario. La cobertura y el mapa
de flujos están en [`../../../docs/E2E.md`](../../../docs/E2E.md).
