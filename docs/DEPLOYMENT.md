# Despliegue — Matrix RH

> Creado por Aldo Garcia.

---

## 1. Modos de despliegue

| Modo | Cuándo | Cómo |
|---|---|---|
| **Windows local (por defecto)** | Equipo de RH, piloto, demo | `install.bat` instala y arranca; `INICIAR_MATRIX_RH.bat` para usos posteriores |
| **Windows con WAMP** | Ya existe WAMP en el equipo | Igual; WAMP provee MySQL y Apache puede actuar de proxy |
| **Contenedores** | Servidor Linux o Windows con Docker | `docker compose up -d` |

En los tres casos el núcleo es el mismo proceso Python 3.12 con FastAPI. **WAMP
no ejecuta el núcleo de IA**: puede proveer MySQL/MariaDB y servir el build del
frontend, pero el backend corre como proceso Python independiente y Ollama como
servicio local.

---

## 2. Instalación en Windows

Requisitos: Python 3.12 x64, uv 0.12.8, runtime de IA y modelos configurados,
MySQL/MariaDB y Node 22.12+ y Corepack para instalar/compilar la interfaz.
El ZIP consolidado incluye un build; omitir su reconstrucción requiere la opción
explícita `-SkipFrontend` y comprobar que ese build esté presente y vigente.

```bash
install.bat
```

El instalador detecta WAMP en `C:\wamp64\www` o `C:\wamp\www` y lo informa. La
ruta de instalación es configurable con `MATRIX_INSTALL_ROOT`; por defecto el
proyecto se opera desde donde se extrajo el ZIP.

Conserva `.env` y las migraciones son idempotentes. Un `.venv` copiado de otra
ruta/servidor se aparta y reconstruye: sus ejecutables no son portables.

---

## 3. Contenedores

`docker-compose.yml` levanta MySQL, Qdrant, el backend y Nginx. Ollama se ejecuta
en el **host** (los modelos ocupan decenas de GB y suelen necesitar GPU), y el
backend lo alcanza por `host.docker.internal`.

```bash
docker compose up -d
```

Servicios:

| Servicio | Puerto interno | Expuesto |
|---|---|---|
| `nginx` | 80/443 | **sí** — único punto de entrada |
| `backend` | 8000 | no |
| `mysql` | 3306 | no |
| `qdrant` | 6333 | no |
| Ollama (host) | 11434 | no |

El backend corre como usuario **no root** dentro del contenedor.

La imagen instala Python desde `uv.lock` con `uv sync --frozen` y el frontend
desde su lock. Antes de `docker compose up -d`, preparar `.env` con los valores
para esta topología: `OLLAMA_BASE_URL=http://host.docker.internal:11434` y
`LLM_LOCAL_HOSTS` incluyendo `host.docker.internal`. `127.0.0.1` dentro del backend
identifica el contenedor, no el host Windows. En Linux configurar la resolución
del host según la topología de Docker y limitar el acceso al runtime.

Las credenciales de `DATABASE_URL` deben coincidir con `MYSQL_*` del servicio
dedicado. `MATRIX_ADOPT_EXISTING_DATABASE=true` sólo autoriza aquí la base vacía
que crea ese servicio para Matrix; no es una instrucción de adoptar bases ajenas.
El Compose conserva el perfil `staging`: antes de producción configurar
`APP_ENV=production`, SSO real y flags de prueba desactivados. El backend usa
`/ready` y Nginx espera su estado saludable; no se conserva una sonda Qdrant que
devolvía éxito sin comprobar el servicio.

La entrega no certifica arranque Docker en el servidor de destino; ejecutar su
aceptación real con certificados, volúmenes y servicios internos aprovisionados.

---

## 4. Variables por entorno

| Variable | development | production |
|---|---|---|
| `APP_ENV` | `development` | `production` |
| `AUTH_PROVIDER` | `local_test` | `oidc` interno o `entra` cloud |
| `LOCAL_TEST_AUTH_ENABLED` | `true` | **`false`** (el arranque falla si no) |
| `LOCAL_TEST_SEED_USERS_ENABLED` | `true` | **`false`** |
| `SESSION_COOKIE_SECURE` | `false` | **`true`** |
| `APP_SECRET_KEY` | autogenerada | **obligatoria**, desde el gestor de secretos |
| `APP_BASE_URL` | `http://127.0.0.1:8000` | URL pública HTTPS |
| `QDRANT_MODE` | `embedded` | `server` recomendado |

`Settings._validate_environment_safety` impide arrancar en producción con el
proveedor local, con el seed activo o sin cookie segura.

---

## 5. Checklist de producción

- [ ] `APP_ENV=production`
- [ ] `AUTH_PROVIDER=oidc` interno o `entra` cloud, cliente confidencial y URLs reales según el [checklist TI](integrations/AD_ACTIVATION_CHECKLIST.md)
- [ ] `LOCAL_TEST_AUTH_ENABLED=false` y `LOCAL_TEST_SEED_USERS_ENABLED=false`
- [ ] Cuentas `Matrix` y `MatrixR1` **eliminadas o deshabilitadas**
- [ ] `APP_SECRET_KEY` desde el gestor de secretos, no en el repositorio
- [ ] `SESSION_COOKIE_SECURE=true` y TLS 1.2+ en el proxy
- [ ] Usuario de MySQL dedicado con permisos mínimos (no `root`)
- [ ] Usuarios **read-only** en cada fuente estructurada externa
- [ ] `QDRANT_MODE=server` con API key
- [ ] Ollama accesible sólo desde el backend
- [ ] Respaldo programado de la base interna
- [ ] `.env` fuera del repositorio y fuera del ZIP
- [ ] `windows\Validate-MatrixRH.ps1` ejecutado desde un entorno limpio

---

## 6. Reverse proxy

`infrastructure/nginx/matrixrh.conf` incluye TLS, cabeceras de seguridad, límite
de tamaño de cuerpo y proxy hacia el backend. Sólo el proxy es accesible desde
fuera; MySQL y Qdrant escuchan en la red interna. Ollama corre en el host (no se
conteneriza) y el backend lo alcanza por `host.docker.internal`.

---

## 7. Actualización

1. `DETENER_MATRIX_RH.bat`
2. Extraer la versión nueva conservando `.env` y `data/knowledge/`
3. `INSTALAR_MATRIX_RH.bat` (idempotente: sólo aplica lo que falta; al terminar
   arranca el sistema)
4. Reingerir y comprobar el corpus: en 1.2.1 el pipeline es 5 y la huella cambia.
   Los chunks de la configuración anterior no se aceptan hasta su reconstrucción.
5. `powershell -ExecutionPolicy Bypass -File windows\Validate-MatrixRH.ps1`

---

## 8. Autoarranque (opcional)

```bash
INSTALAR_MATRIX_RH.bat -WithAutostart
```

Registra una tarea programada **del usuario actual** (no requiere privilegios de
administrador) que arranca Matrix RH al iniciar sesión, sin abrir el navegador.
Para quitarla:

```bash
powershell -ExecutionPolicy Bypass -File windows\Install-Autostart.ps1 -Remove
```

Para la consolidación 1.2.1, seguir [DEPLOYMENT_V2.md](DEPLOYMENT_V2.md) y
[FINAL_CONSOLIDATION.md](FINAL_CONSOLIDATION.md). Los informes 1.1.0 y 1.2.0
siguen siendo históricos; una prueba antigua no certifica el nuevo servidor.
