---
id: PLAN-20261108-diseno-ui
estado: aprobado
rama: agente/diseno-ui
stack: react
zona_protegida: no
autor: claude
---

# Rediseño de la interfaz, alertas y verificaciones

## Objetivo
La interfaz se ve desordenada y con mucho espacio vacío (el editor mide ~3.500 px de alto a 1366 px de ancho). Rediseñarla para que sea compacta y ordenada, y agregar alertas (avisos tipo toast, confirmaciones) y verificaciones del día antes de guardar.

## Reparto (trabajo en paralelo, mismo árbol y misma rama)
- **Claude** hace T1, T2 y T3: `frontend/src/styles.css`, `frontend/src/App.tsx`, `frontend/src/components/Avisos.tsx`, `frontend/src/pages/Reportes.tsx`, `frontend/src/pages/Catalogos.tsx` y sus pruebas.
- **Codex** hace T4 y T5: `frontend/src/verificaciones.ts` (+ test), `frontend/src/editor.css`, `frontend/src/pages/EditorReporte.tsx`, `frontend/src/components/{SelectorColaboradores,TablaCantidades,SelectorFotos}.tsx` y `EditorComponents.test.tsx`.
- **Codex no edita** los archivos de Claude. Para estilos propios del editor usa solo `frontend/src/editor.css` (importado desde `EditorReporte.tsx`). Si necesita una clase global que no existe, la define en `editor.css`.
- Al hacer commit, cada uno agrega **solo sus rutas** (`git add <rutas>`; nunca `git add -A` ni `git add .`).
- `Avisos.tsx` y la base de `styles.css` (T1, T2) ya estarán en la rama cuando Codex empiece. Comprueba con `git log --oneline -3`.

## Fuera de alcance
Backend (ningún archivo en `backend/`), nuevas dependencias npm, tipografías externas, modo oscuro, marcas del mapa, cambiar los Excel/PDF.

## Contrato de diseño (lo provee `styles.css`, T1)
Tokens en `:root`: `--verde-900 #14321e`, `--verde-700 #176b2c`, `--verde-500 #2db34a`, `--verde-50 #eef8f0`, `--fondo #f4f6f5`, `--superficie #fff`, `--borde #dfe6e1`, `--texto #1b2a20`, `--texto-suave #5d6b62`, `--rojo #b42318`, `--rojo-50 #fef3f2`, `--ambar #b54708`, `--ambar-50 #fffaeb`, `--radio 10px`, `--sombra`.

Clases globales disponibles:
| Clase | Uso |
|---|---|
| `.page-header` | Encabezado de página: `<h1>` + `<p class="subtitle">` a la izquierda, acciones a la derecha |
| `.card`, `.card-header`, `.card-title` | Tarjeta blanca con borde y radio; `.card-header` es flex con título y acciones |
| `.stack` (gap 1rem vertical), `.cluster` (flex wrap gap .5rem centrado) | Espaciado |
| `.grid-2`, `.grid-3` | Rejillas responsivas (1 columna bajo 900 px) |
| `button` (primario), `.btn-secondary`, `.btn-ghost`, `.btn-danger`, `.btn-sm`, `.btn-icon` | Botones; `<a class="btn btn-secondary">` para enlaces con aspecto de botón |
| `.field` | `<label class="field"><span>Etiqueta</span><input/></label>` |
| `.badge` + `.badge-ok` / `.badge-warn` / `.badge-error` / `.badge-muted` | Etiquetas de estado |
| `.alert` + `.alert-error` / `.alert-warn` / `.alert-ok` / `.alert-info` | Bloques de alerta en página (`role="alert"` para error, `role="status"` para los demás) |
| `.segmented` | Contenedor de pestañas (`role="tablist"`); los botones hijos con `aria-selected` |
| `.chips`, `.chip`, `.chip.activo` | Selector de personas |
| `.sticky-bar` | Barra inferior fija dentro del contenido (totales + Guardar) |
| `.empty` | Estado vacío |
| `.muted`, `.num` (cifras tabulares) | Texto |

## Contrato de avisos (lo provee `components/Avisos.tsx`, T2)
```ts
export type NivelAviso = "ok" | "error" | "info";
export function useAvisos(): { avisar: (mensaje: string, nivel?: NivelAviso) => void };
export function AvisosProvider({ children }: { children: ReactNode }): JSX.Element; // ya montado en App.tsx
export function Confirmar(props: {
  abierto: boolean; titulo: string; mensaje: string;
  textoConfirmar?: string; peligro?: boolean;
  onConfirmar: () => void; onCancelar: () => void;
}): JSX.Element | null;
```
Los toasts desaparecen solos a los 4 s; los de nivel `error`, a los 8 s. En pruebas, envolver con `AvisosProvider` (el contexto lanza error si falta).

## Tareas

### Tarea 1 — Base visual (Claude)
- **Archivos:** `frontend/src/styles.css`, `frontend/src/App.tsx`.
- **Patrón:** el `styles.css` actual (CSS plano, sin preprocesador).
- **Aceptación:** tokens y clases del contrato; barra lateral con marca; contenido con `max-width: 1280px`; sin scroll horizontal a 375 px.

### Tarea 2 — Avisos y confirmación (Claude)
- **Archivos:** `frontend/src/components/Avisos.tsx`, `frontend/src/components/Avisos.test.tsx`, `frontend/src/App.tsx`.
- **Aceptación:** API del contrato; toasts en región `aria-live="polite"`; `Confirmar` es un diálogo modal con foco en Cancelar y cierre con Escape.
- **Pruebas:** muestra y oculta un toast; Confirmar llama a `onConfirmar` y `onCancelar`.

### Tarea 3 — Reportes y Catálogos (Claude)
- **Archivos:** `frontend/src/pages/Reportes.tsx`, `frontend/src/pages/Catalogos.tsx`, `frontend/src/pages/Catalogos.test.tsx`.
- **Reportes:** tarjeta "Nuevo reporte" que muestra las fechas de la semana elegida y avisa si ese reporte ya existe (deshabilita Crear y ofrece "Abrir"); valida año 2000–2100 y semana 1–53; lista como tabla con insignias de horas y descargas como botones; eliminar con `Confirmar`; toasts al crear y eliminar.
- **Catálogos:** pestañas `.segmented` con contador; buscador; formulario compacto; impide nombres duplicados (sin distinguir mayúsculas ni acentos) con mensaje en línea; desactivar con `Confirmar`; toasts al agregar, editar y desactivar; edición en línea con Cancelar.

### Tarea 4 — Verificaciones del día (Codex)
- **Archivos:** `frontend/src/verificaciones.ts`, `frontend/src/verificaciones.test.ts`.
- **Patrón:** `frontend/src/calculos.ts` (función pura, sin React) y `calculos.test.ts`.
- **Firma:**
  ```ts
  export interface Verificacion { nivel: "error" | "aviso"; mensaje: string; seccion: "actividades" | "herramientas" | "materiales" | "fotos" | "general"; }
  export function verificarDia(entrada: {
    actividades: Actividad[];          // ya pasadas por calcularHoras
    herramientas: Cantidad[]; materiales: Cantidad[];
    fotos: Foto[]; observacion: string; jornada: number;
    nombres: Map<number, string>;      // colaborador_id → nombre
  }): Verificacion[];
  ```
- **Reglas, en este orden y con estos mensajes exactos** (`{X}` es la letra, `{P}` el nombre, `{h}` y `{j}` con `toLocaleString("es")`):
  1. error / actividades — persona cuyo total del día supera la jornada: `"{P} suma {h} h; la jornada es de {j} h."`
  2. error / actividades — asignación con horas vacías o ≤ 0: `"{P} no tiene horas en la actividad {X}."`
  3. error / actividades — actividad con personas y descripción vacía (tras `trim`): `"La actividad {X} tiene personas pero no descripción."`
  4. error / herramientas o materiales — cantidad no finita o ≤ 0: `"La cantidad de {nombre} debe ser mayor que 0."` (nombre del campo `nombre` o `"un elemento"`).
  5. aviso / actividades — descripción sin personas: `"La actividad {X} no tiene personas asignadas."`
  6. aviso / actividades — persona cuyo total es menor que la jornada: `"{P} suma {h} h de {j} h."`
  7. aviso / fotos — actividad con descripción y sin fotos en su espacio: `"La actividad {X} no tiene fotos."`
  8. aviso / general — ninguna actividad con descripción ni personas y observación vacía: `"Día sin actividades: escribe una observación (por ejemplo, feriado)."`
  9. aviso / herramientas — hay personas asignadas y ninguna herramienta: `"No se registraron herramientas."`
- **Pruebas:** un caso por regla, un día completo sin verificaciones, y orden de salida.

### Tarea 5 — Rediseño del editor (Codex)
- **Archivos:** `frontend/src/editor.css` (nuevo), `frontend/src/pages/EditorReporte.tsx`, `frontend/src/components/SelectorColaboradores.tsx`, `TablaCantidades.tsx`, `SelectorFotos.tsx`, `EditorComponents.test.tsx`.
- **Patrón:** el código actual de esos archivos; clases del contrato de diseño; `useAvisos` y `Confirmar` de `components/Avisos.tsx`.
- **Diseño (a 1366 px, un día con 2 actividades y 8 personas debe caber en ≤ 1.800 px de alto):**
  1. `.page-header`: código del reporte, subtítulo con las fechas (`fecha_inicio – fecha_fin`), y a la derecha los tres botones de descarga (`a.btn.btn-secondary.btn-sm`). Debajo, una tarjeta compacta "Firmas" con los dos selects en línea; si falta alguno, insignia `.badge-warn` "Faltan firmas".
  2. Pestañas de días con `.segmented`; cada pestaña muestra el nombre corto en móvil y el completo en escritorio, más la fecha (`dd/mm`). Mantener `role="tab"` y `aria-selected`.
  3. Actividades A, B y C en tarjetas. Una actividad vacía se muestra **plegada** (una línea: "Actividad B · sin capturar" + botón "Capturar"); con datos, desplegada. En cada tarjeta: descripción (textarea de 3 filas), chips de personas, y la tabla de horas en **rejilla de 2 columnas** (en móvil 1): nombre, input de horas de ancho fijo (`5.5rem`), y casilla "Manual" en la misma fila. El encabezado de la tarjeta muestra insignias "N personas" y "H h-h".
  4. Herramientas y Materiales lado a lado (`.grid-2`): select para agregar y filas compactas (nombre · unidad, input de cantidad `6rem`, botón `.btn-ghost.btn-sm` "Quitar"). Estado vacío con `.empty`.
  5. Fotos: una tarjeta con los 4 espacios en `.grid-2` (en pantallas ≥ 1200 px, 4 columnas). Cada espacio: título con contador `n/max` (insignia `.badge-ok` si está completo), miniaturas cuadradas de `120px` con `object-fit: cover`, botón de quitar sobre la miniatura (`.btn-icon`, `aria-label="Eliminar foto {nombre}"`), y una zona de carga tipo botón (`<label class="btn btn-secondary btn-sm">` con el `input[type=file]` visualmente oculto). Mensaje "Subiendo…" con `role="status"`.
  6. "Texto de fotos" y "Observación" en `.grid-2`.
  7. Panel "Verificación" (tarjeta) con el resultado de `verificarDia` más `dia.data.advertencias`: errores con `.alert-error`, avisos con `.alert-warn`; si no hay nada, `.alert-ok` "Todo listo para guardar.".
  8. `.sticky-bar` al final: "Personas N · Horas-hombre H · jornada J h", insignia "Cambios sin guardar" (`.badge-warn`) cuando `sucio`, y botón Guardar. **Guardar se deshabilita si hay verificaciones de nivel error**, con `title` que explique por qué.
- **Alertas:** toast `ok` "Día guardado." al guardar; toast `error` con el mensaje al fallar guardar, subir o eliminar foto; toast `ok` "Foto subida." / "Foto eliminada.". Eliminar foto pide `Confirmar`. Cambiar de día con cambios sin guardar usa `Confirmar` (reemplaza `window.confirm`). Agregar `beforeunload` mientras `sucio`. Si se seleccionan más fotos que las disponibles, toast `info` "Solo se agregaron {n} foto(s); el máximo es {max}.".
- **Conservar:** `serializarDia`, la lógica de borrador y `diaInicializado`, `calcularHoras` en vivo, filtrado de actividades vacías al guardar.
- **Pruebas:** actualizar las existentes; agregar: Guardar deshabilitado con un error de verificación; actividad vacía plegada se despliega con "Capturar"; toast al guardar.

## Seguridad
- #1 Validación: las verificaciones de cliente no sustituyen las del backend (se mantienen).
- #10 Sin datos personales reales en pruebas: usar nombres ficticios.
- n.a.: autenticación, secretos, backend.

## Consistencia
TanStack Query para datos, componentes funcionales, CSS plano, sin librerías nuevas. Textos en español.

## Verificación final
```
npm --prefix frontend run lint && npm --prefix frontend run format:check && npm --prefix frontend run test && npm --prefix frontend run build
```
Más `make check` completo y revisión visual en navegador real (Claude).
