# Checklist de activación AD — Matrix RH 1.2.1

> Creado por Aldo Garcia. Base `94fa083`, cambios v1.2.0 y consolidación v1.2.1.
> Estado: **preparado; activación y aceptación empresarial pendientes de TI**.
> Las pruebas sintéticas no prueban acceso al AD/tenant real.

`ENDPOINTS_REACHABLE` sólo acredita la sonda de discovery/JWKS; no equivale a
`CONNECTED_AND_VALIDATED` ni cierra los pasos de login y permisos de este checklist.

## 1. Identificar el protocolo real

| Ruta | Implementación Matrix | Red | ¿100% local? |
|---|---|---|---|
| Pruebas actuales | `AUTH_PROVIDER=local_test`, Argon2id y sesiones SQL | Sin IdP externo | Sí; sólo development/test |
| Entra ID existente | `AUTH_PROVIDER=entra`, OIDC Authorization Code + PKCE S256 | Navegador/backend → Microsoft HTTPS | No; Entra es cloud aunque las cuentas procedan de AD sincronizado |
| AD DS interno | `AUTH_PROVIDER=oidc`; Keycloak interno federado con AD | Matrix → IdP por OIDC; IdP → AD por LDAPS | Sí, con IdP, AD, DNS, CA y BD internos |
| LDAP/LDAPS directo a Matrix | No hay adapter LDAP ni variables LDAP en Matrix | No aplica | No implementado; no documentar un bind inexistente |
| SAML directo a Matrix | No hay ACS, metadata SAML ni SP implementado | No aplica | No implementado; un broker interno puede ofrecer OIDC a Matrix |

El flag real es `AUTH_PROVIDER`, no `AUTH_MODE`. Se conserva la ruta Entra y su
mapeo. `local_test` no construye el proveedor inactivo, no pide secretos Entra
ni consulta Microsoft. Un error del proveedor activo no activa otro proveedor.

Evidencia: `backend/app/config/settings.py`, `auth/provider.py`,
`auth/entra_provider.py`, `auth/oidc_provider.py`, `api/routes/auth.py`.

## 2. Prerrequisitos y permisos

- [ ] Registrar FQDN y URL HTTPS de Matrix. El navegador y el backend confían en
  la CA de Matrix y del IdP. No usar `verify=False` ni desactivar validación TLS.
- [ ] Sincronizar reloj mediante NTP corporativo. JWT exige issuer/audience,
  firma RS256, exp/iat/nonce; no resolver desfases relajando la validación.
- [ ] Crear cliente OIDC **Web confidencial**, Authorization Code y PKCE S256.
  Desactivar implicit grant y password grant. Redirect exacto:
  `https://matrix.interno/api/v1/auth/callback`; `response_mode=query`.
- [ ] Crear secreto de cliente con vigencia y rotación administradas por TI.
  Matrix implementa `client_secret` en el token endpoint. **No implementa
  autenticación con certificado/private_key_jwt/client_assertion**; la guía
  anterior que ofrecía certificado como intercambiable era incorrecta.
- [ ] El usuario de servicio de Matrix no necesita privilegios de administrador
  de dominio, permiso para escribir AD ni una cuenta de bind LDAP.
- [ ] Sólo para Keycloak + AD: configurar en el **IdP** un bind de lectura
  restringido a las OU y atributos necesarios (identificador estable, username,
  correo opcional y pertenencias). No dar Domain Admin, escritura ni cambios de
  contraseñas. Configurar edit mode READ_ONLY y sincronización conforme a TI.
  El secreto LDAP se guarda en el IdP, nunca en `.env` de Matrix.
- [ ] AD debe ofrecer certificado de servidor válido, EKU Server Authentication,
  FQDN correcto y cadena confiable para el IdP. Habilitar LDAPS con el proceso
  de TI; comprobar conectividad y resolución de grupos antes de abrir Matrix.

| Origen → destino | Puerto/protocolo | Necesidad real |
|---|---|---|
| Navegador → Matrix / IdP | TCP 443 HTTPS | Login, callback, aplicación |
| Backend → IdP | TCP 443 HTTPS | Discovery, JWKS y token endpoint |
| Backend → Microsoft | TCP 443 HTTPS | Sólo `AUTH_PROVIDER=entra` |
| IdP interno → controlador AD | TCP 636 LDAPS | Federación LDAP con TLS |
| IdP → catálogo global | TCP 3269 LDAPS | Sólo si TI usa búsquedas de bosque/GC |
| IdP → AD | TCP 389 + StartTLS | Alternativa explícita de TI; nunca bind simple sin TLS |
| Componentes → DNS / NTP internos | UDP/TCP 53 / UDP 123 | Según infraestructura corporativa |
| Backend → MySQL | TCP 3306 o DSN configurado | Sesiones, roles y estado OIDC; no AD |

No abrir 389/636/3269 hacia Matrix: Matrix no escucha ni consulta LDAP. Kerberos
88/464 y SAML no forman parte de este flujo. Si TI añade otras funciones al IdP,
sus puertos deben documentarse como funciones del IdP.

## 3. Configuración exacta

- [ ] Respaldar `.env`, BD interna y mapeos. Trabajar primero en un clon de
  staging. Aplicar migraciones 0004–0006 con el instalador.
- [ ] Para Entra, completar `ENTRA_ID_SETUP.md`; usar tenant único. Permisos
  solicitados por el código: `openid profile email`. No usa Graph,
  `Directory.Read.All`, `offline_access` ni tokens de refresco.
- [ ] Para OIDC interno, copiar del discovery del realm los valores exactos:

```dotenv
APP_ENV=production
APP_BASE_URL=https://matrix.interno
APP_SECRET_KEY=<64-caracteres-hex-aleatorios>
AUTH_PROVIDER=oidc
LOCAL_TEST_AUTH_ENABLED=false
LOCAL_TEST_SEED_USERS_ENABLED=false
SESSION_COOKIE_SECURE=true
SESSION_COOKIE_SAMESITE=lax
OIDC_ISSUER=https://sso.interno/realms/matrix
OIDC_AUTHORIZATION_ENDPOINT=https://sso.interno/realms/matrix/protocol/openid-connect/auth
OIDC_TOKEN_ENDPOINT=https://sso.interno/realms/matrix/protocol/openid-connect/token
OIDC_JWKS_URI=https://sso.interno/realms/matrix/protocol/openid-connect/certs
OIDC_CLIENT_ID=matrix-rh
OIDC_CLIENT_SECRET=<secreto-administrado-por-TI>
OIDC_REDIRECT_URI=https://matrix.interno/api/v1/auth/callback
OIDC_ALLOWED_GROUPS=
LLM_LOCAL_ONLY=true
```

Los hosts son ejemplos, no valores desplegables. El issuer se compara de forma
exacta, incluida la barra final. No usar `common`/multitenant como sustituto del
tenant Entra configurado. Para Entra, el JWKS correcto es
`https://login.microsoftonline.com/<tenant>/discovery/v2.0/keys`, no
`.../v2.0/.well-known/jwks.json`.

- [ ] En Keycloak configurar mappers que emitan en el **ID token** los claims
  `groups` y/o `roles` como arrays de strings. `realm_access.roles` por sí solo
  no cumple el contrato Matrix. Emitir `preferred_username`, `name` y `sub`
  estables. El sujeto interno es SHA-256 de `issuer|sub`.
- [ ] Usar nombres de cuenta corporativos nuevos o vincular identidades con un
  procedimiento explícito validado por TI. Un username/correo coincidente con
  una cuenta previa **no** vincula automáticamente ni recupera su historial.
- [ ] Preservar el YAML Entra original. Para OIDC crear una copia interna del
  mapeo, poner `provider: oidc` en las entradas, y apuntar a ella mediante el
  nombre conservado `ENTRA_ROLE_MAPPING_FILE=./config/authorization/oidc-role-mapping.yaml`.
- [ ] Cada entrada `external_kind: group` compara `groups`; `app_role` compara
  `roles`. Los IDs/nombres emitidos deben coincidir exactamente. Asignar siempre
  `HCM_EMP_BASICO_MX`; separar Nómina General y Confidencial.
- [ ] `ENTRA_ALLOWED_GROUPS`/`OIDC_ALLOWED_GROUPS` son filtros adicionales de
  grupos, no nombres de app roles. Dejarlos vacíos si el acceso usa sólo roles.
  Tokens con group overage se rechazan; Matrix no consulta Graph.

Desde la raíz, con BD y configuración disponibles:

```bat
set "PYTHONPATH=%CD%\backend"
.venv\Scripts\python.exe -m scripts.load_entra_mapping --dry-run
.venv\Scripts\python.exe -m scripts.load_entra_mapping --prune
.venv\Scripts\python.exe -m scripts.preflight --read-only
```

Revisar el dry-run antes de `--prune`: aplica cambios de permisos. El dry-run no
es una aprobación automática del contenido del YAML.

## 4. Pruebas obligatorias de TI

- [ ] Con `local_test`, login sintético y consulta funcionan con Microsoft/IdP
  bloqueados. Las pruebas incluidas verifican que no se construye Entra.
- [ ] Con el proveedor seleccionado, discovery/JWKS responden y coinciden.
  `ENDPOINTS_REACHABLE` sólo prueba endpoints; un login real aún es obligatorio.
  `/ready` devuelve 503 ante proveedor activo sin conectar o metadata incorrecta.
- [ ] Login base: `/api/v1/me` expone sólo permisos concedidos. Base + dominio
  añade sólo ese dominio. Especializado sin base no concede roles HCM.
- [ ] Dos navegadores: callback copiado del A al B debe ser rechazado. Cookie
  `matrixrh_oidc_state`: HttpOnly, Secure, SameSite=Lax, 600 s, path `/api/v1/auth`.
- [ ] Reutilizar state, alterar nonce, issuer, audience, firma o exp debe fallar.
  El state se consume una sola vez incluso si falla el canje del código.
- [ ] Retirar rol, revocar sesiones y volver a entrar: historial y resumen
  restringidos desaparecen; una respuesta pendiente con alcance anterior no se
  publica. Probar explícitamente la matriz de Nómina.
- [ ] Caída del IdP: no hay fallback a local. Cerrar sesión revoca la sesión
  Matrix; **no garantiza cerrar la sesión global del IdP**. El endpoint logout
  actual no redirige al logout federado.
- [ ] En el perfil totalmente local bloquear egress a Internet y repetir login,
  consulta, embeddings, ingesta y búsqueda vectorial con servicios internos.
- [ ] Registrar fecha, servidor, versión, issuer, perfiles y evidencia de pruebas
  sin tokens, secretos ni datos personales en el repositorio.

La sincronización AD/IdP y los claims llegan a Matrix en el login. Revocar un
grupo en AD no actualiza instantáneamente una sesión ya iniciada. Para corte
inmediato TI debe revocar las sesiones Matrix y gestionar la sincronización del
IdP. La reversión nunca reactiva cuentas sintéticas en producción.

## Fuentes primarias contrastadas

- [Microsoft: OIDC v2 y discovery](https://learn.microsoft.com/en-us/entra/identity-platform/v2-protocols-oidc).
- [Microsoft: Authorization Code + PKCE](https://learn.microsoft.com/en-us/entra/identity-platform/v2-oauth2-auth-code-flow).
- [Microsoft: certificados y activación LDAPS](https://learn.microsoft.com/en-us/troubleshoot/windows-server/active-directory/configure-ldap-over-ssl).
- [Keycloak: federación LDAP](https://www.keycloak.org/docs/latest/server_admin/index.html#_ldap).
