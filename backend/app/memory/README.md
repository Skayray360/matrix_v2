<!-- Creado por Aldo Garcia. -->

# app/memory/

Memoria conversacional por usuario y conversación.

## Garantías

- Ownership verificado en **todas** las rutas; no basta con ocultar en la UI.
- Una conversación ajena devuelve **404**, no 403: un 403 confirmaría que el
  identificador existe.
- Nunca se mezclan conversaciones de distintos usuarios.
- Al reconstruir el contexto se descartan los turnos que se apoyaron en
  categorías que el rol actual **ya no** tiene autorizadas.
- No se almacena chain-of-thought interno del modelo.

## El resumen es de diálogo, no de contenido

El prompt de resumen prohíbe explícitamente incluir cifras, políticas concretas o
nombres de documentos. Si el resumen almacenara contenido, sobreviviría a un
cambio de permisos y se convertiría en un canal de fuga.

El prompt no basta como control de autorización. Desde 1.2.0 mensajes y resúmenes
guardan un alcance verificable y su reutilización depende de los permisos
vigentes. El historial aplica el mismo filtro; filas históricas sin procedencia
se ocultan conservadoramente. La ventana reciente y el cursor de resumen
impiden volver a resumir sólo los primeros 200 mensajes.
