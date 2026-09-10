# Aceptación sintética de un modelo local

Creado por Aldo Garcia.

`backend/scripts/model_smoke_test.py` comprueba el contrato real de `ModelClient`
contra los runtimes configurados en `.env`. No instala ni descarga modelos. La
prueba requiere servicios locales ya preparados y autorización explícita para
consumir inferencia. Ejecutar desde `backend`, usando el venv **raíz** creado
por `install.bat`:

```powershell
..\.venv\Scripts\python.exe -m scripts.model_smoke_test --run-inference --profile all --output ..\reports\smoke-all-local.json
```

En Linux instalado por `scripts/matrixrh.sh`, sustituir el ejecutable por
`../.venv/bin/python`. Si se preparó manualmente con `uv sync` desde `backend/`,
el ejecutable está en `.venv/bin/python` o `.venv\Scripts\python.exe` dentro de
esa carpeta: no crear otro venv sólo para ejecutar la sonda. `--profile deep` utiliza
el perfil profundo; `--profile all` ejecuta los dos perfiles por separado, incluso
si comparten nombre de modelo. No se cambian modelos automáticamente ni se activa
cloud. Repetir con un nombre de informe nuevo: no sobrescribe archivos existentes.

Sin `--run-inference`, el comando solo muestra ayuda y sale con código **2**:
**INCOMPLETE**, no se ha realizado ninguna prueba de modelo. Con el permiso, sale
con **0** si todas las comprobaciones pasan y **1** si alguna falla o no puede
guardar el informe. No confundir una ejecución unitaria con transporte simulado
con la aceptación del modelo real.

## Alcance y comprobaciones

1. Exige `LLM_LOCAL_ONLY=true` y rechaza cualquier perfil Vertex antes de conectar.
   El constructor del adapter también valida los endpoints y la lista de hosts
   locales aprobados. Una lista de hosts no sustituye el aislamiento de red de TI.
2. Comprueba el inventario de los tres roles configurados: rápido, profundo y
   embeddings. Si falta un modelo configurado, no inicia generaciones. El
   inventario reúne nombres de los runtimes configurados: **un nombre presente
   no prueba que esté disponible en el runtime del perfil correcto**. La llamada
   real de embeddings y las generaciones de cada perfil seleccionado verifican
   esa disponibilidad. Usar `--profile all` para comprobar ambos perfiles; una
   ejecución `fast` no acredita inferencia del perfil `deep`.
3. Exige la revisión de embeddings que utiliza el RAG para identificar su índice:
   `LLM_EMBEDDING_REVISION` no puede estar vacía ni ser `unverified` para el runtime
   compatible; Ollama debe devolver el digest del modelo. Si falta, la sonda falla
   antes de generar, aunque el modelo figure en el inventario. No publica la
   revisión ni el digest en el informe. Esta comprobación no sustituye la
   verificación por TI de que la revisión declarada corresponde a los pesos.
4. Solicita dos embeddings con las plantillas configuradas de consulta/documento,
   verifica la dimensión y rechaza vectores nulos. No inserta nada en Qdrant.
5. Envía una evidencia sintética pequeña y verifica de forma independiente la
   respuesta numérica. Usa el contexto, límite de salida y temperatura del perfil.
6. Solicita el `StructuredQueryPlan.model_json_schema()` real del proyecto y
   valida el JSON, las restricciones Pydantic y el plan sintético esperado. **No
   ejecuta SQL ni accede a bases corporativas.** Usa el presupuesto del planner;
   un límite insuficiente para un modelo con razonamiento debe fallar la prueba,
   no aceptarse una respuesta truncada.

El JSON guarda códigos de resultado, indicadores, latencias y recuentos de tokens
cuando el runtime los entrega. No guarda prompts, respuestas, razonamiento,
embeddings, URL, claves ni mensajes de excepción. Un fallo de contrato requiere
revisar el runtime local y sus logs bajo los controles de TI; el informe no imprime
el contenido recibido para facilitar un diagnóstico a costa de exponer datos.

## Lo que no demuestra

Una ejecución exitosa acredita únicamente **ese contrato sintético** con la
configuración usada. No certifica calidad RAG corporativa, instrucciones extensas,
contexto máximo efectivo, soporte multimodal, GPU/VRAM suficiente, entrenamiento,
concurrencia de 200–250 usuarios ni una mejora frente a otro modelo. Esas
aceptaciones necesitan corpus de evaluación, hardware y servicios reales. Conservar
por separado el inventario/digest del artefacto y la configuración saneada usada
para comparar resultados sin publicar secretos.
