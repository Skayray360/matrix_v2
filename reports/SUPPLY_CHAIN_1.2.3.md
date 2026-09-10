<!-- Creado por Aldo Garcia. -->
# Cadena de suministro del frontend — 1.2.3

Fecha de ejecucion: 2026-09-10. Base revisada: Matrix RH 1.2.2; controles
corregidos integrados en 1.2.3. El gestor real del proyecto es **npm**, no pnpm:
`npm@11.9.0`, con SHA-512 fijado en `frontend/package.json` y ejecutado por
Corepack. No se modificaron versiones de dependencias como parte de esta
auditoria: los avisos consultados no justificaron cambiar el lock validado.

## Dictamen y evidencia

**No se encontraron vulnerabilidades conocidas por npm audit, paquetes de la
denylist ni IOC configurados en las dependencias inspeccionadas.** Este
resultado es temporal y no demuestra ausencia de malware desconocido.

| Verificacion ejecutada | Resultado |
|---|---|
| `corepack npm --version` | 11.9.0; Node 24.19.0 en el entorno de prueba |
| `corepack npm audit --json` sobre proyecto | 0 avisos: criticos, altos, moderados, bajos e informativos |
| `corepack npm audit --omit=dev --json` | 0 avisos conocidos en alcance produccion |
| Instalacion nueva en directorio temporal, sin reutilizar `node_modules` | 152 paquetes; `npm ci --ignore-scripts --no-audit --no-fund` termino correctamente |
| Auditoria npm repetida sobre instalacion nueva | 0 avisos conocidos; 175 entradas totales en el lock |
| Denylist y escaneo ampliado del arbol nuevo | 152 manifiestos reales inspeccionados, 0 hallazgos bloqueantes |
| Identidad de paquetes instalados frente al lock | Sin divergencias; las entradas opcionales para otras plataformas pueden faltar |
| Experimento real con `preinstall`, `install`, `postinstall` sinteticos | Ninguno se ejecuto con `npm ci --ignore-scripts --offline` |
| Frontend contra instalacion nueva | 29/29 pruebas Vitest, typecheck y build aprobados |
| Suite focal de suministro, instalacion y quality gate | 76 aprobadas, 1 omitida; incluye 34 pruebas nuevas |
| Ruff de archivos modificados y `bash -n scripts/matrixrh.sh` | Aprobados |

La omision corresponde a la prueba Linux de propiedad de PID: `/proc` del
entorno no permite observar el hijo. No es una aprobacion de dicho caso. No se
ejecutaron Windows/PowerShell, Docker ni GitHub Actions reales; sus secuencias
se verificaron mediante contratos estaticos. No se ejecutaron Playwright ni
servicios de produccion como parte de esta auditoria de instalacion.

Los 175 paquetes del lock y los 152 instalados **no deben sumarse**: el lock
contiene tambien paquetes opcionales de plataformas distintas. La instalacion
emitio una advertencia de deprecacion para `whatwg-encoding@3.1.1`; deprecacion
no equivale a una vulnerabilidad reportada. Tambien se observo una advertencia
de npm sobre la configuracion `http-proxy` del entorno de ejecucion.

## Bugs confirmados y correcciones

| Componente | Bug y causa raiz | Fix aplicado |
|---|---|---|
| Verificador: lock | Comprobaba existencia del lock pero no su contenido; un paquete bloqueado no instalado aun pasaba | Modo `--lock-only` analiza todas las entradas npm, incluidas opcionales, antes de descargar; exige HTTPS, integridad y coherencia con dependencias declaradas |
| Verificador: identidad | No contrastaba manifiestos instalados con las versiones/rutas bloqueadas en el lock | Bloquea versiones o identidades diferentes, paquetes sobrantes, manifiestos invalidos y paquetes obligatorios ausentes |
| Verificador: arbol ausente | Devolvia exito sin `node_modules` inspeccionado | El modo completo falla si no hay arbol; el modo solo-lock declara explicitamente que la inspeccion posterior esta pendiente |
| Verificador: nombres | Omitia paquetes reales llamados `test`, `src`, `lib` o `dist` | Identifica raices de paquetes por su posicion bajo `node_modules`, incluidos scopes y dependencias anidadas |
| Verificador: contenido | Omitia JavaScript mayor de 2 MiB y no inspeccionaba otros scripts | Lectura por bloques con solapamiento, sin descartar bundles grandes; incluye JS/TS, JSON/YAML, scripts shell/PowerShell/batch/Python y archivos sin extension |
| Verificador: configuracion | Una linea `ignore-scripts=true` seguida de `false` o un valor con prefijo `true` pasaba | Exige una unica declaracion inequivoca; el gate tambien bloquea `packageManager` sin hash completo |
| Verificador: enlaces | Un ejecutable enlazado fuera del arbol podia quedar fuera del control | Bloquea enlaces externos y raices de paquetes enlazadas; permite los enlaces internos normales de `.bin` |
| Windows/Linux | La denylist se comprobaba despues de descargar y no se exigia auditoria actual completa antes de instalar | Lock local y audit online bloqueantes antes de `npm ci`; escaneo del arbol despues de instalar y antes de compilar |
| Docker/CI | Ejecutaban Vite antes del gate de suministro | Misma secuencia pre-descarga/post-instalacion; Docker incorpora Python/PyYAML solo a la etapa frontend para ejecutar el mismo verificador |
| Quality gate | Avisos dev eran informativos y el flujo ejecutaba herramientas JS aun tras fallar suministro | Audit de build/test tambien bloqueante; no ejecuta Vitest, Vite ni Playwright si suministro o audit no aprueban |
| Validacion Windows | La inspeccion ocurria despues de Playwright | Inspeccion y audit antes del bloque E2E; lo omite, sin marcarlo aprobado, cuando no hay validacion de suministro |
| Alcance de auditoria/instalacion | `NODE_ENV=production` u opciones `omit` del entorno podian excluir herramientas de build | Los caminos automatizados incluyen explicitamente dev, optional y peer para el build/audit completo |

La denylist historica `config/supply_chain_denylist.yaml` **se conserva**. Su
procedencia documentada es un aviso interno: esta entrega no convierte ese
aviso en una confirmacion independiente de que cada version fue comprometida.
Cada coincidencia sigue siendo bloqueante hasta revision de TI.

## Secuencia de instalacion futura

Los instaladores de Windows/Linux, Docker y CI ejecutan estos controles en este
orden. Desde `backend/`, con su entorno Python activo:

```bash
python -m scripts.verify_supply_chain --lock-only
```

Desde `frontend/`, para la auditoria online y descarga:

```bash
corepack npm audit --audit-level=low --include=dev --include=optional --include=peer
corepack npm ci --ignore-scripts --no-audit --no-fund --include=dev --include=optional --include=peer
```

De nuevo desde `backend/`, antes de ejecutar herramientas del frontend:

```bash
python -m scripts.verify_supply_chain --json
```

Solo si todos los pasos anteriores terminan con codigo cero, desde `frontend/`:

```bash
corepack npm run typecheck
corepack npm test
corepack npm run build
```

No usar `npm audit fix --force`, instalaciones sin lock ni `npm rebuild` para
silenciar un fallo. Si la auditoria no puede consultar el registro, la
instalacion online se detiene: no se interpreta el error de red como ausencia
de vulnerabilidades. Los pasos manuales tambien deben detenerse al primer
codigo de salida distinto de cero.

Windows `install.bat -Offline` conserva la operacion con caches preparadas: no
consulta avisos actuales y lo advierte. TI debe aprobar esas caches/artefactos
en un entorno de preparacion conectado o con un registro interno de avisos.
El frontend compilado puede desplegarse sin herramientas Node en el runtime;
`-SkipFrontend` usa ese build preexistente, no audita ni recompila sus fuentes.

Para inspeccionar otra copia sin alterar el proyecto:

```bash
python -m scripts.verify_supply_chain --frontend /ruta/a/copia/frontend --lock-only
python -m scripts.verify_supply_chain --frontend /ruta/a/copia/frontend --json
```

El soporte historico para inspeccionar un arbol pnpm no significa que los
instaladores actuales usen pnpm, ni que el analizador de lock npm certifique un
`pnpm-lock.yaml`.

## Limites y fuentes tecnicas

`npm ci` comprueba el lock, no lo actualiza, elimina el `node_modules` previo
del **directorio objetivo** y respeta `--ignore-scripts`. Por ese motivo se
probo primero en un directorio temporal. `npm run build/test` sigue ejecutando
la accion solicitada: bloquear lifecycle hooks no elimina el riesgo de cargar
una dependencia maliciosa durante el build. [Documentacion oficial de npm ci](https://docs.npmjs.com/cli/v11/commands/npm-ci/).

`npm audit` consulta vulnerabilidades conocidas y comunica al registro
configurado nombres/versiones de dependencias; no ingesta documentos RH ni
ejecuta inferencia cloud. La consulta online pertenece a preparacion/CI y no es
una dependencia del chat local. [Documentacion oficial de npm audit](https://docs.npmjs.com/cli/v11/commands/npm-audit/).

La integridad SRI del lock protege el tarball durante `npm ci`; el contraste
posterior de este proyecto comprueba identidad/version/ruta e IOC, **no vuelve
a verificar criptograficamente cada archivo extraido contra el tarball**. No
certifica que el paquete original sea benigno, binarios nativos, dependencias
del propio Corepack/npm, CVE futuros, codigo ofuscado sin IOC ni un host ya
comprometido. Los patrones de contenido son heuristicos y acotados, con
solapamiento de 4096 caracteres entre bloques. [Formato oficial de package-lock.json](https://docs.npmjs.com/cli/v11/configuring-npm/package-lock-json/).

Si TI confirma una instalacion previa de un paquete comprometido, actualizar
el lock no demuestra que el servidor este limpio: se requiere tratar ese
evento con el procedimiento corporativo de respuesta a incidentes antes de
autorizar el despliegue.
