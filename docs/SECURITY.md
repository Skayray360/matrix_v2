# Seguridad — Matrix RH

> Creado por Aldo Garcia.

Documento de controles implementados. El análisis de amenazas está en
[`THREAT_MODEL.md`](THREAT_MODEL.md).

---

## 1. Principios aplicados

- **Mínimo privilegio**: cada rol recibe exactamente lo que necesita; no existen
  permisos de "SQL arbitrario", "leer secretos" ni "ver el system prompt".
- **Deny-by-default**: la ausencia de una regla nunca concede acceso.
- **Defensa en profundidad**: cada control crítico está respaldado por al menos
  otro independiente.
- **Fail closed**: ante duda, error o dependencia caída, se deniega.

---

## 2. Autenticación

Ver [`AUTHENTICATION_AUTHORIZATION.md`](AUTHENTICATION_AUTHORIZATION.md).

Resumen: OIDC Authorization Code + PKCE con patrón BFF para Entra ID; proveedor
local con Argon2id restringido a `development`/`test`; sesión de servidor con
cookie `HttpOnly` y hash del token en la base; CSRF por token de sesión en toda
petición mutante; rate limiting por IP y por usuario; bloqueo temporal por
intentos fallidos; mensajes de error idénticos para usuario inexistente y
contraseña incorrecta.

---

## 3. Autorización

- `UserContext` inmutable y firmado con HMAC-SHA256.
- Decisión **antes** de RAG, **antes** del SQL y **antes** del prompt.
- El filtro de categorías viaja dentro de la consulta a Qdrant.
- Ownership estricto de conversaciones (404, no 403, ante recursos ajenos).
- La wildcard administrativa se resuelve a una lista enumerada; nunca se eliminan
  filtros.

---

## 4. Gestión de secretos

| Regla | Implementación |
|---|---|
| Ningún secreto en el código | Verificado por `scripts/secrets_scan.py` y `bandit` |
| Sólo `.env.example` en el repositorio | `.env` está en `.gitignore` |
| Secretos por entorno o gestor | `Settings` usa `SecretStr`; `pydantic-settings` lee del entorno |
| DSN de fuentes externas | `sources.yaml` guarda el **nombre** de la variable, nunca el valor |
| El frontend nunca recibe secretos | El bundle no contiene ninguna variable sensible; verificado en E2E |
| Sin tokens en `localStorage` | La sesión es cookie `HttpOnly`; verificado en E2E |
| Redacción en logs | Se aplica en el *formatter*, no en el llamador |

### Supresiones del escáner

Cada supresión requiere un marcador inline con justificación:

```python
# secrets-scan: allow (JWT sintetico sin firma valida, fixture de redaccion)
```

Todas las supresiones se publican íntegras en
`reports/security/secrets_scan.json` para revisión.

---

## 5. Criptografía

| Uso | Algoritmo | Nota |
|---|---|---|
| Contraseñas locales de test | **Argon2id** (t=3, m=64 MiB, p=2) | Nunca SHA para contraseñas |
| Integridad de documentos | SHA-256 | Huella para detectar cambios |
| Firma del `UserContext` | HMAC-SHA256 | Clave `APP_SECRET_KEY` |
| Token de sesión en la BD | SHA-256 del token | El token en claro sólo viaja en la cookie |
| Seudonimización en logs | HMAC-SHA256 truncado | Hash del conjunto de roles |
| TLS | 1.2 mínimo, 1.3 preferido | Terminado en el proxy |
| Cifrado aplicativo (si se requiere) | AES-256-GCM vía `cryptography` | La clave no vive en el repositorio |

Cookies: `HttpOnly` siempre; `Secure` obligatorio en producción (validado en la
configuración, el arranque falla si no); `SameSite` configurable con `lax` por
defecto.

---

## 6. Carga de archivos

1. Allowlist de extensiones (`.docx`, `.md`, `.pdf`, `.txt`, `.xlsx`, `.csv`).
2. Verificación de **magic bytes** frente a la extensión declarada.
3. Tamaño máximo configurable (25 MB por defecto) y máximo de archivos por
   petición.
4. Nombre interno UUID; el `filename` del cliente jamás se usa como ruta.
5. Normalización y bloqueo de `..`, rutas absolutas y unidades de Windows.
6. Almacenamiento fuera del web root (`var/uploads/<user>/<conversation>/`).
7. Límites anti-zip-bomb para OOXML: entradas, tamaño descomprimido y ratio.
8. Límites de páginas, hojas, filas y celdas en los extractores.
9. Sin ejecución de macros, fórmulas ni contenido incrustado.
10. Sanitización en el render (el frontend construye nodos React, no HTML).

Desde 1.2.0 hay lectura por bloques con límite acumulado, cuota por propietario,
cupo de cargas y extracción en proceso separado con vigilancia de tiempo/RSS.
La validación de la aplicación complementa el límite del cuerpo en el proxy.
La vigilancia no constituye un sandbox de SO ni limita el pico de memoria con
precisión absoluta entre muestras.

**El lote completo se valida antes de tocar infraestructura**: un archivo
rechazado devuelve 415/413 aunque el almacén vectorial esté caído, y no queda
medio lote indexado.

---

## 7. Acceso a datos estructurados

El LLM **no envía SQL**. El flujo es:

```
plan JSON -> Pydantic (extra=forbid) -> QueryPolicyValidator
   -> compilador parametrizado -> verificación AST (sqlglot)
   -> timeout + row limit -> credencial read-only
```

Bloqueado por construcción: `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`,
`CREATE`, `EXEC/CALL` no autorizado, múltiples sentencias, comentarios SQL,
`UNION` y subconsultas.

Sobre el uso de f-string en el ensamblado del SQL: los identificadores no pueden
viajar como parámetros en ningún motor. La mitigación es de tres capas
(allowlist → regex de identificador + citado → parámetros + re-verificación por
AST) y está documentada como riesgo residual aceptado en
`reports/security/cybersecurity.md`.

Recomendación operativa: usar **vistas de seguridad** en la propia base además del
control aplicativo.

---

## 8. Cabeceras y CSP

Aplicadas por el backend (no sólo por el proxy), porque el arranque por doble
clic no lleva proxy delante:

```
Content-Security-Policy: default-src 'self'; script-src 'self';
  style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self' data:;
  connect-src 'self'; object-src 'none'; frame-ancestors 'none';
  base-uri 'self'; form-action 'self'
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Referrer-Policy: no-referrer
Permissions-Policy: geolocation=(), microphone=(), camera=(), payment=()
Cross-Origin-Opener-Policy: same-origin
Cross-Origin-Resource-Policy: same-origin
Cache-Control: no-store
Strict-Transport-Security: max-age=31536000; includeSubDomains   (si TLS)
```

`script-src` no incluye `unsafe-eval` ni `unsafe-inline`. `style-src` admite
`unsafe-inline` porque React inyecta estilos calculados; los scripts, que son el
vector real de XSS, no.

---

## 9. XSS en el frontend

El renderizador de Markdown (`frontend/src/security/Markdown.tsx`) **construye
elementos de React** en lugar de generar HTML. No se usa
`dangerouslySetInnerHTML` en ninguna parte del proyecto, por lo que un
`<img onerror=...>` incrustado en un documento corporativo o en una respuesta del
modelo se muestra como texto literal.

Además, una cita cuyo `source_id` no está en la lista de fuentes recibidas se
renderiza como texto plano, sin apariencia de fuente verificada.

---

## 10. Observabilidad y auditoría

Logs JSON con: `timestamp`, `request_id`, `conversation_id`, `user_opaque_id`,
`role_set_hash`, `intent`, `selected_model`, `selected_tools`, `source_ids`,
`authorization_decision`, `latency_ms`, `status`, `error_code`.

**No se registran**: contraseñas, client secrets, bearer tokens, llaves privadas,
documentos completos ni prompts completos.

`/health` (proceso vivo) y `/ready` (dependencias obligatorias operativas) tienen
semántica distinta a propósito: si `health` dependiera de MySQL, un reinicio de la
base tumbaría el contenedor entero.

---

## 11. Manejo de errores

Al cliente sólo llegan `code`, `message` y `request_id`. Nunca stack traces,
rutas internas, SQL ni secretos. Los errores de validación de Pydantic **no**
hacen eco del payload recibido: podría reflejar una credencial escrita por error
en un campo equivocado.

Códigos definidos: `unauthorized`, `forbidden`, `unsupported_file`,
`file_too_large`, `extraction_failed`, `ingestion_failed`, `ollama_unavailable`,
`embedding_dimension_mismatch`, `qdrant_unavailable`, `database_unavailable`,
`structured_query_rejected`, `insufficient_evidence`, `out_of_scope`,
`policy_missing`, `not_found`, `validation_error`, `rate_limited`,
`configuration_error`, `internal_error`.

---

## 12. Exposición de red

Sólo el proxy es accesible desde fuera. MySQL, Qdrant y Ollama escuchan en
`127.0.0.1`. **Ollama no debe exponerse a Internet ni a redes no confiables** —
carece de autenticación.

---

## 13. Cadena de suministro

Una amenaza contemplada en la cadena npm es un **gusano autopropagable**. Un
paquete comprometido puede ejecutar código
en el ciclo de vida de instalación, roba credenciales del entorno (`NPM_TOKEN`,
`GITHUB_TOKEN`, credenciales cloud) y republica paquetes del mantenedor afectado
para propagarse. La víctima no necesita ejecutar la aplicación: basta con
instalar.

> **El gestor por sí solo no es la defensa.** La versión 1.1.0 usaba pnpm;
> la consolidación usa la versión npm declarada mediante Corepack, fijada con SHA-512 en
> `packageManager`, y `package-lock.json`. Ambos consumen paquetes del mismo
> ecosistema. Se conservan bloqueo de scripts de instalación, lock e inspección
> del árbol; cambiar de gestor no demuestra ausencia de paquetes comprometidos.

### El control central: no ejecutar scripts de instalación

```ini
# frontend/.npmrc  (lo leen npm y pnpm)
ignore-scripts=true
```

Con esa línea se bloquean los scripts de ciclo de vida de los paquetes durante
la instalación. Algunos paquetes pueden declararlos sin que se ejecuten; el
verificador los informa. La compilación se ejecuta explícitamente y tiene su
validación propia; `ignore-scripts` no convierte el build en un sandbox.

### Instalación congelada sin scripts de ciclo de vida

| Comando | Comportamiento |
|---|---|
| `npm install` / `pnpm install` (sin flags) | Puede **resolver rangos** y traer una versión publicada hace minutos. Sin bloqueo efectivo de scripts, también puede ejecutarlos. |
| `corepack npm ci --ignore-scripts --no-audit --no-fund --include=dev --include=optional --include=peer` | Instala lo fijado en `package-lock.json`; falla si no está sincronizado, bloquea scripts e incluye las herramientas de compilación aunque el entorno omita dependencias dev. |

Aplicado en `windows/Install-MatrixRH.ps1`, `scripts/matrixrh.sh`,
`backend/Dockerfile` y `.github/workflows/implementation-v2.yml`, y documentado en el README. El Dockerfile **no** tiene
fallback a una instalación sin fijar: si el lockfile está desincronizado, el
build falla en lugar de degradarse.

Desde 1.2.3, todos estos caminos siguen el orden **verificar lock → consultar
avisos completos → instalar sin lifecycle hooks → inspeccionar árbol →
compilar**. La auditoría online falla ante avisos de severidad baja o superior,
o si no pudo verificarlos; no descarga dependencias ni compila tras ese fallo.
Windows `-Offline` omite expresamente la consulta de avisos actuales y exige
caches previamente aprobadas por TI. No se presenta esa omisión como un audit
aprobado. Los comandos `corepack npm ...` se ejecutan desde `frontend/`, donde
Corepack encuentra el `packageManager` fijado.

### Verificación automática del árbol instalado

Desde la raíz del proyecto:

```bat
set "PYTHONPATH=%CD%\backend"
.venv\Scripts\python.exe -m scripts.verify_supply_chain --lock-only
.venv\Scripts\python.exe -m scripts.verify_supply_chain
```

El primer comando comprueba el lock antes de descargar y declara que falta
inspeccionar el árbol instalado; no certifica `node_modules`. El segundo
comprueba el árbol **realmente instalado** y falla si está ausente. Son
comandos para el entorno `.venv` que crea el instalador en la raíz. Si usa
`backend/.venv` para desarrollo, ejecute `python -m scripts.verify_supply_chain`
desde `backend/`, con ese entorno activado.

Comprueba seis aspectos del lock y del árbol instalado:

1. **Lista de bloqueo** — ningún paquete/versión de
   `config/supply_chain_denylist.yaml` está presente, **a ninguna profundidad**
   (un paquete comprometido suele ser una dependencia transitiva). También
   analiza entradas del lock aún no instaladas, incluidas las opcionales.
2. **Scripts de instalación** — informa los paquetes que declaran `preinstall`,
   `install` o `postinstall`; no los ejecuta.
3. **Indicadores de compromiso** — nombres de archivo y patrones de contenido
   asociados a exfiltración: `webhook.site`, `npmjs.help`,
   `api.github.com/user/repos`, lectura de `NPM_TOKEN`/`GITHUB_TOKEN` seguida de
   una petición de red. Escanea bundles grandes por bloques con solapamiento,
   sin omitirlos por superar 2 MiB, y amplía las extensiones de scripts revisadas.
4. **Reproducibilidad** — existe el lock del gestor declarado (`package-lock.json`
   desde 1.2.1) y `.npmrc` declara una única asignación inequívoca
   `ignore-scripts=true`; una asignación posterior contradictoria bloquea.
5. **Integridad del gestor** — `packageManager` en `package.json` fija npm con
   hash de integridad (`npm@x.y.z+sha512...`). Desde 1.2.3, el gate completo y el
   modo solo-lock lo exigen de forma **bloqueante**, igual que el empaquetado.
6. **Coherencia del lock npm** — exige HTTPS e integridad para descargas,
   dependencias declaradas coherentes y correspondencia de identidad,
   versión y ruta con el árbol instalado. Bloquea manifiestos inválidos,
   paquetes sobrantes, paquetes obligatorios ausentes y enlaces externos.

Se ejecuta en el **preflight** (cada arranque), en el **instalador** (bloquea la
compilación si falla), en el **quality gate** y en `windows\Validate-MatrixRH.ps1`.
El preflight permite operar un runtime con frontend ya compilado y sin
`node_modules`: en ese caso registra **WARN/no inspeccionado**, no una
certificación del árbol. `-SkipFrontend` tampoco vuelve a auditar un build
preexistente. El quality gate y la validación Windows no ejecutan
Vite/Vitest/Playwright si el árbol o las auditorías npm no aprueban.

### Riesgos del gestor (corepack / `packageManager`) y su mitigación

El frontend usa **npm** mediante **Corepack**, que TI debe aprovisionar junto a
Node; no se asume que toda distribución lo incluya. La versión y su integridad
están fijadas en `packageManager`:

| Riesgo | Mitigación |
|---|---|
| corepack **descarga el gestor npm** la primera vez; sin hash, la descarga sólo confía en TLS y el registro | Fijar `packageManager` **con hash de integridad** (`npm@x.y.z+sha512...`): corepack **verifica criptográficamente** el binario. `verify_supply_chain` y `package_release` lo **exigen** (falla-cerrado). |
| **Fetch externo** en instalación (rompe la operación offline) | Aprovisionar el gestor y caches npm/uv de Windows. `-Offline` fija `COREPACK_ENABLE_NETWORK=0` y exige que todos los artefactos estén disponibles. |
| **Descarga silenciosa** (`COREPACK_ENABLE_DOWNLOAD_PROMPT=0`, necesario para instalar desatendido) | El pin/hash limita el artefacto aceptado; el modo offline prohíbe esa descarga. |
| Cambiar de gestor **no** reduce el riesgo de gusanos | pnpm usa el **mismo registro** que npm; la defensa real son los puntos 1–6 de arriba. |

El hash oficial de npm 11.9.0 ya está fijado en el proyecto; el operador no
necesita regenerarlo ni ejecutar `corepack use` durante una instalación. Desde
`frontend/`, este comando utiliza el pin/hash existente:

```bash
corepack npm --version
```

Actualizar el gestor requiere una revisión separada de la versión, del hash
oficial y de los resultados de instalación/auditoría; no se sustituye el pin
por un rango ni se desactiva su verificación para resolver un error de red.

Se conservan las pruebas históricas de árboles sintéticos en
`backend/tests/security/test_supply_chain.py`; 1.2.3 agrega 34 casos en
`backend/tests/security/test_supply_chain_123.py`, incluidos IOC entre bloques,
lock frente a árbol y prevención de ejecución tras un gate fallido. No
descargan malware real.

### Mantener la lista de bloqueo

`config/supply_chain_denylist.yaml` es datos, no código. Cuando se publique un
incidente nuevo, añada el paquete y las versiones afectadas. Acepta versión
exacta, lista de versiones o el comodín `*`.
La lista histórica procede de un aviso interno y se conserva como política de
bloqueo; esta entrega no confirma independientemente el compromiso de cada
versión enumerada.

### Auditoría de vulnerabilidades

Ejecute los comandos npm desde `frontend/`. Ejecute los comandos Python desde
`backend/`, con su entorno virtual activo.

| Comando | Umbral |
|---|---|
| `corepack npm audit --omit=dev --audit-level=low` | **Bloqueante**: es lo que se despliega |
| `corepack npm audit --audit-level=low --include=dev --include=optional --include=peer` | **Bloqueante desde 1.2.3**: Vite/Vitest también ejecutan código en el host de build |
| `pip-audit --strict` | Informativo, revisado por el Agente de Ciberseguridad |
| `bandit -r app` | Bloqueante |

Los resultados 1.1.0 se conservan en sus informes históricos. Los avisos de la
consolidación y la fecha de consulta se registran en
[FINAL_CONSOLIDATION_VALIDATION.md](../reports/FINAL_CONSOLIDATION_VALIDATION.md);
no se hereda un cero de un análisis antiguo.
La revisión 1.2.3 y sus límites están en
[SUPPLY_CHAIN_1.2.3.md](../reports/SUPPLY_CHAIN_1.2.3.md). Cero avisos conocidos o
IOC no demuestra ausencia de malware desconocido. La integridad SRI se
verifica durante `npm ci`; este escáner no compara criptográficamente cada
archivo extraído con el tarball original. La auditoría online comunica al
registro configurado nombres/versiones de paquetes, no documentos RH, y no
forma parte de la inferencia local durante la operación.

### Resto de la cadena

- Dependencias con versión **fija** (`==` en Python, exacta en el frontend) y `save-exact=true`.
- Registro oficial declarado en `.npmrc`; cualquier cambio de registro o
  configuración de mayor precedencia debe revisarse con los locks e integridad.
- Extras opcionales para drivers de motores no usados: reducen la superficie.
- Playwright descarga navegadores sólo de forma **explícita**
  (`corepack npm run e2e:install`), nunca implícita al instalar.

---

## 14. Reporte de vulnerabilidades

Ver [`../SECURITY.md`](../SECURITY.md) en la raíz del repositorio.
