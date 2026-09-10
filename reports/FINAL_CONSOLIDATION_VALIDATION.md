# Validación de la consolidación — Matrix RH 1.2.1

> Creado por Aldo Garcia. Fecha: 2026-09-10.
> Entrega completa del código, con frontend compilado. La aceptación del servidor
> empresarial requiere las comprobaciones de destino indicadas al final.

## 1. Versiones comparadas

| Origen | Identificador | Uso en esta entrega |
|---|---|---|
| GitHub `Skayray360/matrix`, `main` consultada | `94fa083b59553df18040150b4b714ae25afa5cbc` | Lógica de negocio, estructura, taxonomía, contratos y documentación de 1.1.0 |
| Revisión local 1.2.0 | `472607fb268ae2277f7d4de1be012998f6cc5663` | Correcciones de la auditoría y requisitos R1–R5, revisadas antes de consolidar |
| Consolidación 1.2.1 | Rama `release/consolidated-1.2.1` | Correcciones finales, paquete completo e historial Git incluido |

El changelog del README registra cada componente, causa raíz y corrección en la
misma entrega. `docs/FINAL_CONSOLIDATION.md` explica las decisiones; el inventario
completo está en `reports/FINAL_SOURCE_COMPARISON.md`.

## 2. Conservación comprobada

- Los **272 archivos versionados de la base GitHub siguen presentes**.
- Las migraciones originales **0001–0003 conservan sus bytes**; se mantienen las
  ampliaciones 0004–0006 de la revisión 1.2.0.
- Las configuraciones originales de autorización conservan sus bytes. Los
  cambios de documentación no modifican las concesiones ni las categorías.
- No se eliminó ninguna ruta HTTP declarada en los routers originales. Se
  conservan las dos rutas nuevas de consulta/cancelación de operaciones de 1.2.0.
- Se mantienen identidad fija, chat general, consulta documental, resumen de
  adjuntos, planes estructurados validados, memoria y publicaciones autorizadas.
- Se conservan todos los documentos originales; los informes 1.1.0/1.2.0 se
  identifican como históricos. No se presentan sus pruebas como pruebas actuales.

La comparación de archivos y rutas no demuestra por sí sola equivalencia de
comportamiento: las pruebas siguientes cubren los contratos revisados.

## 3. Pruebas ejecutadas

Entorno: Linux, Python 3.12.14, uv 0.12.8, Node.js 24.19.0; frontend ejecutado
mediante Corepack con npm 11.9.0 fijado por SHA-512. El destino Windows usa
Python 3.12 x64 y Node 22 LTS 22.12+ con Corepack, según la guía.

| Comprobación | Resultado observado |
|---|---|
| Backend: `pytest backend/tests/unit backend/tests/security --tb=short` | **572 aprobadas, 37 omitidas, 0 fallidas**; 609 casos |
| Motivos de omisión | 36 requieren MySQL/MariaDB; 1 necesita visibilidad del proceso hijo en `/proc`, no disponible en este sandbox |
| Frontend: instalación desde lock mediante `corepack npm ci --ignore-scripts --no-audit --no-fund` | Correcta; 152 paquetes instalados |
| Frontend: `corepack npm run typecheck` | Aprobado, sin emitir JavaScript junto al TypeScript |
| Frontend: `corepack npm test` | **24 aprobadas, 0 fallidas** |
| Frontend: `corepack npm run build` | Aprobado; `frontend/dist/index.html` y recursos compilados incluidos en el ZIP |
| Dependencias Python: pip-audit | **0 avisos conocidos en 95 dependencias auditables**; Matrix, paquete privado, no está en PyPI y se revisó como código |
| Dependencias frontend: npm audit, árbol completo | **0 avisos conocidos**, 175 dependencias registradas, incluidas las de desarrollo |
| Cadena de suministro del frontend instalado | 151 manifiestos; sin bloqueos, scripts automáticos ni indicadores detectados; lockfile, `ignore-scripts` y pin con hash aprobados |
| Ruff: código de aplicación, scripts y nuevas regresiones | Aprobado |
| SAST Bandit: aplicación | Sin hallazgos pendientes tras revisión de las dos llamadas relativas al parser aislado |
| Shell: `bash -n scripts/matrixrh.sh` | Aprobado |
| Encabezados y escaneo de secretos | Aprobados; cero secretos reales detectados por el escáner del proyecto |
| `git diff --check` | Aprobado |

Bandit identifica el uso de `subprocess` del extractor. Se documentan dos
excepciones locales B404/B603: intérprete y módulo fijos, argumentos como datos,
entorno reducido y `shell=False`. No se desactivó Bandit ni sus demás reglas.
El análisis sigue emitiendo un aviso por una anotación B608 histórica sin
hallazgo asociado. El cliente de pruebas también avisa de la deprecación de
httpx en Starlette; ninguno se presenta como una prueba funcional fallida.

Los catálogos de vulnerabilidades y los escáneres no prueban ausencia absoluta
de problemas. Las cifras son las observadas en esta ejecución.

## 4. Regresiones reproducidas y cerradas

- Orden DOCX: una tabla de Vacaciones ya no termina bajo el encabezado Becas.
- Contexto: la excepción situada después del carácter 2.200 se conserva como
  parte de la unidad o se informa el límite; no se corta en silencio.
- Grounding: se rechaza eliminar sujetos, negaciones y condiciones, incluso
  cuando la excepción está en otro párrafo de la misma evidencia.
- Magnitudes: `.5 → 5` y `-12 → 12` se rechazan; copias exactas se conservan.
- Citas: identificadores ambiguos entre documentos distintos no acreditan una
  respuesta. Una fila SQL necesita conservar las columnas que le dan sentido.
- Memoria extensa cede espacio antes de descartar evidencia completa que cabe.
- Consulta de maternidad con evidencia de comedor y dos generaciones rechazadas
  devuelve insuficiencia, sin presentar ese texto como respuesta documental.
- Resúmenes mantienen fallback extractivo completo y presupuesto acotado. La
  fidelidad textual se registra separada de una verificación factual semántica.
- Adjuntos anteriores se migran sin duplicar IDs ni cambiar ámbito; rutas
  Windows/POSIX se reconstruyen dentro del almacenamiento actual y se verifica
  el SHA-256. Un fallo conserva la generación anterior y queda registrado.
- Identidad fija permanece en el historial; conversación general no se marca
  documentalmente fundamentada.
- Proveedores rechazan envelopes, índices, vectores o respuestas incompletas
  incorrectos; el schema real del plan SQL conserva los tipos permitidos.
- Bases de datos con migraciones ajenas no se reconocen como propiedad de
  Matrix; los nombres con `_` se comparan exactamente.
- Cambios de conversación no pierden identificadores de reintento ni recuperan
  listas obsoletas; los borradores no enviados se conservan.

Estas pruebas usan documentos sintéticos, SQLite/Qdrant locales y transportes
controlados cuando corresponde. No constituyen una evaluación del modelo real
ni de la información empresarial.

## 5. Contenido y ejecución

El ZIP contiene fuentes completas, frontend compilado, `uv.lock`,
`package-lock.json`, `.env.example`, scripts BAT/PowerShell/shell, migraciones,
semillas y corpus sintéticos, documentación, pruebas e historial Git
`source-history.bundle`. `SHA256SUMS.txt` permite verificar los archivos del
paquete. Los resultados binarios y caches de pruebas no se confunden con fuente.

En Windows: preparar los prerrequisitos y `.env` según el README y ejecutar
`install.bat`. La cadena original de BAT instala y después arranca. La opción
`-SkipFrontend` usa el build incluido; la instalación normal lo vuelve a
compilar con las dependencias fijadas. `-Offline` requiere caches y pesos
preparados para Windows; el ZIP no contiene dependencias ni modelos descargados.

Se excluyen credenciales reales, bases de datos, sesiones, adjuntos reales,
pesos de modelos, `node_modules`, venvs, sus respaldos, caches y enlaces
simbólicos. No se activaron AD/Entra/Vertex ni fuentes empresariales.

## 6. Aceptación pendiente en el destino

1. Ejecutar el instalador y los contratos PowerShell en un Windows limpio con
   MySQL/MariaDB, Ollama, modelos y controladores reales. Aquí no hay Windows,
   PowerShell ni esos servicios. Las comprobaciones estáticas no sustituyen esa
   instalación integral.
2. Validar migraciones/seed y actualización de una copia de la base real, con
   respaldo; comprobar chat, adjuntos, ingesta y recuperación tras reinicio.
3. Completar el checklist TI de AD/IdP y probar login, logout y revocación. Una
   sonda de metadata/JWKS no acredita el SSO completo.
4. Medir calidad en preguntas reales aprobadas por RH. El control extractivo
   puede rechazar paráfrasis correctas; además, los 900 tokens estimados por
   fragmento y los 768 de salida del perfil rápido requieren calibración con el
   modelo real. Copiar un texto no demuestra que responda a la pregunta.
5. Definir SLO y ejecutar carga real de 200 usuarios sostenidos/250 en pico.
   Los cupos por proceso evitan admisión ilimitada, pero no acreditan esa
   capacidad ni sustituyen una cola compartida para varios procesos API.
6. Validar la alternativa Docker en un host con Docker, configuración de red,
   credenciales e IdP. Aquí se revisó el contrato; no se construyó ni arrancó
   la imagen.

GitHub `main` no fue modificada por esta consolidación. La integración había
rechazado la publicación de 1.2.0 con HTTP 403; esta entrega proporciona el
proyecto y su historial completos. El workflow se conserva preparado; no se
declara una ejecución de GitHub Actions que no ocurrió.
