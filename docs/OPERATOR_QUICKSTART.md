<!-- Creado por Aldo Garcia. -->

# Inicio rápido para el operador

## Primera instalación en Windows

1. Extraiga el ZIP en una ruta local estable; por ejemplo,
   `C:\Apps\Matrix RH`.
2. Inicie MySQL/MariaDB (WAMP es opcional) y el runtime configurado.
3. Confirme Python 3.12 x64, uv 0.12.8, Node 22.12+ y Corepack y los modelos del `.env`.
4. Ejecute `install.bat` con doble clic.
5. Espere `INSTALACION COMPLETADA`; si falla, no cree tablas, PID ni archivos
   `.env` manualmente: ejecute `DIAGNOSTICO_MATRIX_RH.bat`.
6. Confirme el arranque automático y la URL configurada. `INICIAR_MATRIX_RH.bat`
   queda para arranques posteriores.

El instalador reutiliza una instalación propia, pero no adopta ni modifica una
base preexistente sin autorización explícita. Si el nombre configurado ya está
ocupado, elige un nombre libre y conserva la base ajena.

## Dependencias y controles antes de compilar

El gestor de esta entrega es **npm mediante Corepack**, fijado con hash en
`frontend/package.json`; no ejecute `pnpm install` ni una instalación sin lock
para resolver un fallo. `install.bat` comprueba primero el lock y los avisos
actuales, instala con `npm ci --ignore-scripts`, inspecciona el árbol obtenido
y solo entonces compila. Las dependencias de desarrollo también son
bloqueantes, porque ejecutan Vite/Vitest en el equipo de compilación.

Para revisar manualmente una instalación ya existente, desde la raíz del
proyecto en CMD, usando el `.venv` creado por el instalador:

```bat
set "PYTHONPATH=%CD%\backend"
.venv\Scripts\python.exe -m scripts.verify_supply_chain --json
```

Después, desde `frontend/` para que Corepack detecte el gestor fijado:

```bat
cd frontend
corepack npm audit --audit-level=low --include=dev --include=optional --include=peer
cd ..
```

Deténgase ante cualquier fallo; no compile ni ejecute pruebas JS para
silenciarlo. Un error de red durante el audit no significa que no haya
vulnerabilidades. El modo completo del verificador falla sin `node_modules`;
`--lock-only` solo inspecciona el lock antes de descargar, no certifica el
árbol instalado. El preflight puede advertir que no hay `node_modules` cuando
se usa un frontend ya compilado: eso permite el runtime, no aprueba un audit.

`install.bat -Offline` exige caches preparadas por TI y advierte que no consultó
avisos actuales. `-SkipFrontend` reutiliza un build existente: no lo vuelve a
auditar ni compilar. Consulte [los controles de suministro](SECURITY.md#13-cadena-de-suministro)
y [la evidencia 1.2.3](../reports/SUPPLY_CHAIN_1.2.3.md).

## Operación normal

| Acción | Archivo |
|---|---|
| Instalar e inicializar (instala y arranca) | `install.bat` (delega en `INSTALAR_MATRIX_RH.bat`) |
| Iniciar backend e interfaz (usos posteriores) | `INICIAR_MATRIX_RH.bat` |
| Detener sólo los procesos del proyecto | `DETENER_MATRIX_RH.bat` |
| Diagnóstico de sólo lectura | `DIAGNOSTICO_MATRIX_RH.bat` |
| Validación integral | `powershell -ExecutionPolicy Bypass -File windows\Validate-MatrixRH.ps1` |
| Autoarranque opcional | `INSTALAR_MATRIX_RH.bat -WithAutostart` |

`/health` significa que el proceso vive; `/ready` significa que sus dependencias
obligatorias están listas. Una respuesta positiva de `/health` no reemplaza
`/ready`.

## Diagnóstico mínimo

1. Ejecute `DIAGNOSTICO_MATRIX_RH.bat`.
2. Corrija el **primer** `FAIL`; los fallos siguientes pueden ser consecuencia.
3. Revise `var\logs\backend-*.err.log` si el proceso termina al arrancar.
4. Confirme los modelos exactos con `ollama list` y su carga con `ollama ps`.
5. Confirme que el archivo documental tiene estado `indexed` antes de probar su
   resumen.

No publique `.env`, contraseñas administrativas, tokens, logs completos ni
documentos empresariales al solicitar soporte. Comparta el código de error, el
check que falla y el mensaje seguro del diagnóstico.

## Credenciales de desarrollo

Las cuentas `Matrix` y `MatrixR1` son fixtures sintéticos para
`APP_ENV=development|test`; no son cuentas corporativas. Deben deshabilitarse
antes de producción y nunca deben coexistir con el proveedor local activo en
`APP_ENV=production`.

Para operación detallada consulte [`RUNBOOK.md`](RUNBOOK.md) y, ante un fallo,
[`TROUBLESHOOTING.md`](TROUBLESHOOTING.md).

Checklist vigente 1.2.1 y pruebas pendientes de servidor nuevo:
[DEPLOYMENT_V2.md](DEPLOYMENT_V2.md). Comparación e inventario de la entrega:
[FINAL_CONSOLIDATION.md](FINAL_CONSOLIDATION.md).
