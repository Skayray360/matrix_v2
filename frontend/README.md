<!-- Creado por Aldo Garcia. -->

# frontend/

Interfaz de Matrix RH: React 18 + TypeScript + Vite.

| Ruta | Contenido |
|---|---|
| `src/pages/` | `LoginPage`, `ChatPage` |
| `src/components/` | Conversaciones, mensajes, composer, accesos rápidos y panel de trazabilidad |
| `src/security/` | Renderizador Markdown seguro |
| `src/services/` | Cliente HTTP |
| `tests/` | Pruebas de componentes (Vitest) |
| `tests/e2e/` | Playwright |

## Comandos

La instalacion usa **Node.js 22.12+**, Corepack y el `package-lock.json` del
repositorio. `packageManager` fija npm 11.9.0 con su SHA-512; `corepack npm`
verifica ese gestor y evita depender de la version global de npm. TI debe
aprovisionar Node/Corepack y, para un destino sin Internet, precargar el gestor
y los paquetes de la plataforma Windows. El gate de empaquetado verifica el pin.

```bash
corepack npm ci --ignore-scripts --no-audit --no-fund
corepack npm run typecheck
corepack npm run build
corepack npm test
corepack npm run e2e
```

`corepack npm ci` falla si el lock no coincide con `package.json`. Los scripts de
instalacion siguen deshabilitados en `.npmrc` y en el instalador. Para un destino
sin Internet precargue el cache de npm para Windows o distribuya el build
validado y use `install.bat -SkipFrontend -Offline`.

## Decisiones

- **Same-origin**: en desarrollo Vite hace proxy de `/api` al backend, para que la
  cookie `HttpOnly` + `SameSite` funcione igual que en producción.
- **Sin tokens en el navegador**: la sesión es una cookie que el JavaScript no
  puede leer. Nada en `localStorage` ni `sessionStorage`.
- **Sin `dangerouslySetInnerHTML`** en ninguna parte.
- **Misma interfaz para todos los roles**: la diferencia de información viene del
  backend. Ocultar un botón no es un control de seguridad.
- **Accesos rápidos sin privilegios**: cada tarjeta sólo envía un prompt normal;
  pasa por la misma intención, autorización, RAG y auditoría que el texto escrito.
- **Trazabilidad acotada**: el panel usa `intent`, `latency_ms`, `grounded` y las
  fuentes de la respuesta actual. No abre un endpoint administrativo ni muestra
  prompts, chunks, secretos o categorías no autorizadas.
- **Adjunto privado visible**: el composer distingue la carga de conversación
  del corpus corporativo; su ubicación visual no cambia el namespace técnico.

La actualización visual 1.1.0 conserva el cliente y los endpoints existentes:
`/me`, conversaciones, `/chat`, CSRF y carga privada. El build precompilado del
ZIP es el que sirve FastAPI en operación normal.

La consolidacion **1.2.1** mantiene esa interfaz y su estructura. Conserva los
borradores y los identificadores de envio incierto por conversacion y mensaje;
reconcilia el historial al volver a una conversacion con respuesta pendiente y
descarta listas obsoletas tras una eliminacion. La carga de un adjunto bloquea
el envio hasta terminar su procesamiento. Las pruebas de componentes cubren
estos recorridos; la cancelacion solicita al backend descartar la respuesta y
no garantiza detener inmediatamente el proceso de inferencia.

`typecheck` valida con `tsc --noEmit`: no genera archivos JavaScript junto al
fuente TypeScript. El changelog completo esta en el README de la raiz.

Validacion de la entrega 1.2.1 (2026-09-10): Node 24.19.0, npm 11.9.0 mediante
Corepack, instalacion desde lock con scripts deshabilitados, typecheck y build
correctos, **24 pruebas de componentes aprobadas**. Vitest se fija en 4.1.11
para corregir [GHSA-82fw-gwwq-j7x9](https://github.com/vitest-dev/vitest/security/advisories/GHSA-82fw-gwwq-j7x9),
un aviso del servidor de desarrollo. `npm audit` del arbol completo registro
cero avisos conocidos en 175 dependencias. Estas pruebas usan respuestas HTTP
controladas; no certifican los servicios reales, Windows, AD ni concurrencia.
