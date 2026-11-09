---
id: PLAN-20261108-despliegue-nube-parte2
estado: cerrado         # borrador | aprobado | en_ejecucion | cerrado
rama: agente/despliegue-nube        # misma rama; se ejecuta después de la parte 1
stack: node
zona_protegida: sí      # flujo de inicio de sesión en el cliente
autor: claude
descartado: "2026-11-08 — Oscar decidió quedarse en local y seguir guardando los reportes. No se ejecutó."
---

# Despliegue en la nube — parte 2: frontend en Vercel con reportes en memoria

## Objetivo
Que el frontend funcione en Vercel contra el backend de Render: inicio de sesión, catálogos y un editor donde la semana vive **solo en la pestaña abierta**. Desde ahí se descargan el formato, el mejorado y el PDF enviando todo a `POST /api/exportar/{tipo}`. Requiere la parte 1 aceptada.

## Decisiones de Oscar (2026-11-08)
- Los reportes no se guardan: se generan y se descargan.
- La semana vive solo mientras la pestaña está abierta. Si se cierra o se recarga, se pierde, y la app avisa antes.
- El mapa y el logo siguen fijos en el backend.

## Contexto
- `frontend/src/api/client.ts`: `fetch(`/api${path}`)` relativo y sin `Authorization`.
- `frontend/src/api/reportes.ts`: tipos (`Actividad`, `Asignacion`, `Cantidad`, `Foto`, `Dia`, `DiaInput`, `LETRAS`, `Letra`) y llamadas a endpoints que la parte 1 **elimina** (`listarReportes`, `crearReporte`, `eliminarReporte`, `verReporte`, `editarReporte`, `verDia`, `guardarDia`, `subirFoto(s)`, `eliminarFoto`).
- `frontend/src/pages/Reportes.tsx` (330 líneas): lista y crea reportes guardados.
- `frontend/src/pages/EditorReporte.tsx` (637 líneas):
  - Usa `useQuery`/`useMutation` por día, `borrador` + `sucio`, `armarActividades`, `espaciosFotos`, `puedeQuitar`, `siguienteLetra`, `calcularHoras` y `verificarDia`.
  - Descargas con `<a href>` (`:276-288`).
  - Fotos con `SelectorFotos` y `<img src={foto.url}>`.
- `frontend/src/actividades.ts`, `calculos.ts` y `verificaciones.ts`: funciones puras que se conservan.
- `frontend/src/App.tsx`: rutas `/`, `/reportes/:id` y `/catalogos`; la barra lateral dice "Uso local · 127.0.0.1".
- `frontend/nginx.conf`: CSP y cabeceras.

## Alcance
**Dentro:** URL de API y token, login y rutas protegidas, editor de semana en memoria, compresión de fotos en el navegador, descargas por POST, `vercel.json` y documentación.

**Fuera de alcance:** backend (parte 1), guardar borradores (ni en el servidor ni en el navegador), mapa editable, registro y recuperación de contraseña, despliegue real.

## Tareas

### Tarea 1 — Cliente: URL configurable, sesión y login
- **Archivos:** `frontend/src/api/client.ts`, `frontend/src/api/sesion.ts` (crear), `frontend/src/api/auth.ts` (crear), `frontend/src/vite-env.d.ts`, `frontend/src/pages/Login.tsx` (crear), `frontend/src/App.tsx`, y las pruebas `client.test.ts` y `Login.test.tsx` (crear).
- **Patrón a seguir:** `client.ts` (`apiRequest`, `ApiError`); `pages/Catalogos.tsx` (formulario, `useMutation`, `useAvisos`); `pages/Reportes.test.tsx` (montaje).
- **Seguridad:** #1, #6, #9, #11, #15.
- **Qué hacer:**
  1. `API_URL = import.meta.env.VITE_API_URL ?? ""` y las peticiones a `${API_URL}/api${path}`.
  2. `sesion.ts`: `obtenerToken`, `guardarToken(token, expiraEn)` y `cerrarSesion`. Guarda en `sessionStorage` la clave `sg_sesion` (`{token, expira_en}`); un token expirado se trata como inexistente. Todo con `try/catch`. Suscriptor `alCerrarSesion(cb)`.
  3. `apiRequest` agrega `Authorization: Bearer` si hay token; un 401 llama a `cerrarSesion()`. Agrega `apiDescarga(path, body: FormData) -> {blob, nombre}` (POST, mismo manejo de errores) que lee el nombre de `Content-Disposition`.
  4. `auth.ts`: `iniciarSesion(correo, contrasena)` y `verUsuario()`.
  5. `Login.tsx`:
     - Campos con `autoComplete` `username` y `current-password`.
     - Mensajes según el `code`: `credenciales_invalidas` → "Correo o contraseña incorrectos."; `demasiados_intentos` → "Demasiados intentos. Espera 15 minutos."; error de red → "No se pudo conectar con el servidor."
     - Si tarda más de 3 s: "Conectando con el servidor… (puede tardar hasta un minuto)".
  6. `App.tsx`:
     - `RequerirSesion` redirige a `/login`. `alCerrarSesion` navega a `/login` y hace `queryClient.clear()`.
     - La barra lateral muestra el correo y el botón "Cerrar sesión", y quita "Uso local · 127.0.0.1".
     - Rutas: `/login`, `/` (editor de la tarea 2) y `/catalogos`.
- **Criterio de aceptación:** `npm --prefix frontend run test` y `build` pasan.
- **Pruebas requeridas:**
  - Prefijo de `VITE_API_URL` en la URL.
  - Cabecera `Authorization` con token y sin él.
  - Un 401 cierra la sesión.
  - Un token expirado no se envía.
  - `apiDescarga` lee el nombre del archivo.
  - En el login: redirección sin sesión, login correcto, mensaje del 401 y mensaje del 429.

### Tarea 2 — Editor de la semana en memoria
- **Archivos:** `frontend/src/semana.ts` (crear), `frontend/src/semana.test.ts` (crear), `frontend/src/pages/EditorReporte.tsx`, `frontend/src/components/SelectorFotos.tsx`, `frontend/src/api/reportes.ts`, `frontend/src/pages/Reportes.tsx` (eliminar) y `Reportes.test.tsx` (eliminar), `frontend/src/components/EditorComponents.test.tsx`.
- **Patrón a seguir:** `actividades.ts`/`calculos.ts` (funciones puras con prueba) y el `EditorReporte.tsx` actual (estructura visual, pestañas de días, tarjetas, verificaciones y `beforeunload`).
- **Seguridad:** #14 (solo UX; el backend valida), #15, #16 (comprimir no reemplaza la validación del backend).
- **Qué hacer:**
  1. `semana.ts`:
     - Tipos `FotoLocal{id: string, espacio: Letra | "AD", archivo: Blob, url: string, nombre: string}`, `DiaLocal{dia_semana, fecha, observacion, texto_fotos, actividades, herramientas, materiales, fotos: FotoLocal[]}` y `SemanaLocal{anio, semana, elaborado_por_id, revisado_por_id, dias: DiaLocal[6]}`.
     - `crearSemana(anio, semana)`: fechas ISO de lunes a sábado, `actividades = armarActividades([])` y `texto_fotos = "Fotos antes y después de la actividad realizada"`.
     - `semanaActualISO(hoy)`.
     - `armarFormData(semana)`: arma el JSON `datos` con la forma exacta de `ReporteExportar` de la parte 1. Filtra las actividades vacías como hoy, usa `serializarDia` para los campos y numera las fotos con un `indice` global en el orden en que se agregan a `fotos`.
     - `comprimirFoto(file): Promise<Blob>`: usa `createImageBitmap` + `canvas`, lado máximo 1600 px y `toBlob("image/jpeg", 0.82)`. Si el navegador no puede, devuelve el archivo original.
  2. `api/reportes.ts`: quita todas las llamadas a endpoints eliminados y conserva los tipos y `serializarDia`.
  3. `EditorReporte.tsx` sin `useParams` ni consultas de reporte:
     - Arriba, selector de año y semana (por defecto la semana ISO actual) y el botón "Nueva semana" (si hay datos, pide confirmación con `Confirmar`).
     - El estado `SemanaLocal` vive en `useState`. Las pestañas de días, las actividades (agregar y quitar), herramientas, materiales, observación, texto de fotos, firmantes y verificaciones funcionan igual que hoy sobre el día activo. **Desaparece el botón "Guardar día"**: los cambios ya están en memoria.
     - Fotos: `SelectorFotos` recibe `FotoLocal[]`. Al elegir archivos los comprime, crea `URL.createObjectURL` y respeta el máximo de 4 por espacio. "Eliminar" quita la foto y revoca la URL. Al desmontar o con "Nueva semana" se revocan todas.
     - Aviso `beforeunload` si hay cualquier dato capturado. Texto visible fijo bajo el encabezado: "Esta semana no se guarda: descarga los archivos antes de cerrar la pestaña."
  4. Elimina `Reportes.tsx`, su prueba y su ruta.
- **Criterio de aceptación:**
  - `test`, `lint`, `format:check` y `build` pasan.
  - `rg -n "guardarDia|verDia|subirFoto|listarReportes|crearReporte|/reportes/" frontend/src` → 0 resultados.
- **Pruebas requeridas:**
  - `crearSemana(2026, 45)` → fechas del 02/11 al 07/11.
  - `armarFormData` produce el JSON esperado (6 días, actividades vacías filtradas, `indice` correlativo) y adjunta los blobs en ese orden.
  - En el editor: capturar una actividad en el lunes, cambiar al martes y volver conserva el lunes.
  - Una quinta foto en un espacio → aviso de máximo.
  - "Nueva semana" con datos pide confirmación.

### Tarea 3 — Descargas por POST
- **Archivos:** `frontend/src/components/BotonDescarga.tsx` (crear) y su prueba, `frontend/src/pages/EditorReporte.tsx`.
- **Patrón a seguir:** componentes de `frontend/src/components/` y `useAvisos`.
- **Seguridad:** #6, #15.
- **Qué hacer:**
  - `BotonDescarga({tipo, etiqueta, semana})` llama a `apiDescarga(`/exportar/${tipo}`, armarFormData(semana))`, crea un `<a download>` temporal con el nombre del servidor y revoca la URL al terminar.
  - Mientras trabaja: deshabilitado y "Generando…". Si pasan más de 5 s, "Generando… (el servidor puede estar despertando)".
  - Errores con `useAvisos`, usando el `detail` del backend (p. ej. 413 "Las fotos superan el máximo…").
  - Tres botones (formato, mejorado y PDF) en el encabezado del editor, en lugar de los `<a href>`.
  - Si las verificaciones tienen errores (`hayErrores`), los botones se deshabilitan con el mismo criterio con que hoy se deshabilitaba "Guardar".
- **Criterio de aceptación:**
  - Las pruebas pasan: el POST lleva `FormData` con `datos` y los blobs, el nombre del archivo viene del servidor, se muestra el aviso de error y se ve el estado "Generando…".
  - `rg -n 'href=\{`/api' frontend/src` → 0.
- **Pruebas requeridas:** las del criterio.

### Tarea 4 — Vercel y documentación
- **Archivos:** `frontend/vercel.json` (crear), `frontend/.env.example` (crear), `README.md`.
- **Patrón a seguir:** las cabeceras de `frontend/nginx.conf`.
- **Seguridad:** #1, #18, #19.
- **Qué hacer:**
  - `vercel.json`:
    - SPA con `rewrites: [{ "source": "/(.*)", "destination": "/index.html" }]`.
    - `headers` iguales a `nginx.conf` con `connect-src 'self' https://reportes-servicios-api.onrender.com`, `img-src 'self' data: blob:` y HSTS.
  - `.env.example`: `VITE_API_URL=https://reportes-servicios-api.onrender.com`.
  - README, sección "Vercel":
    - Raíz `frontend` con Vite, el comando `npm run build` y la salida `dist`.
    - `VITE_API_URL` = URL real de Render. Si cambia, hay que ajustar también `connect-src`.
    - Poner la URL de Vercel en `CORS_ORIGINS` de Render.
  - En local, `VITE_API_URL` vacío sigue usando el proxy de nginx.
- **Criterio de aceptación:**
  - `build` pasa y `vercel.json` es JSON válido.
  - `make up` local (con `ADMINS_SEMILLA` en el `.env` local y **después** de que Oscar respalde `data/`): login con el admin semilla, capturar lunes y martes con fotos, descargar los tres archivos y revisar que el Excel tenga las fotos. Al recargar, la semana se pierde tras el aviso.
- **Pruebas requeridas:** la prueba manual de `make up`, documentada en el reporte.

## Seguridad

| # | Medida | Aplica | Cómo se cumple / prueba |
|---|---|---|---|
| 1 | API keys | sí | Solo `VITE_API_URL` (pública); ninguna llave de Supabase. gitleaks. |
| 6 | Autenticación | sí | `RequerirSesion` (UX); el backend responde 401. Prueba de redirección. |
| 9 | Sesión | sí | `sessionStorage` (no `localStorage`) con expiración de 8 h, borrado con un 401 o al cerrar la pestaña. Sin cookies, porque son dominios distintos. Riesgo de XSS mitigado con la CSP estricta y la medida 15. |
| 11 | Rate limiting | sí | Se muestra el 429. Prueba en `Login.test.tsx`. |
| 14 | Validar inputs | sí (UX) | Máximo 4 fotos y verificaciones; la validación real está en el backend. |
| 15 | Sanitizar | sí | Sin `dangerouslySetInnerHTML`; `rg` = 0. |
| 16 | Archivos | sí | `accept="image/*"` y compresión, sin reemplazar la validación de Pillow del backend. |
| 18 | Headers | sí | `vercel.json` con CSP, `nosniff`, `DENY`, `Referrer-Policy`, `Permissions-Policy` y HSTS. |
| 19 | HTTPS | sí | Vercel + HSTS; `VITE_API_URL` con `https://`. |
| 20 | Dependencias | sí | Sin dependencias nuevas; `npm audit --audit-level=high`. |

n.a.: 2–5, 7, 8, 10, 12, 13, 17 (son del backend o no aplican al cliente).

## Consistencia
- Se reutilizan `apiRequest`/`ApiError`, React Query (catálogos y login), `useAvisos`/`Confirmar`, `actividades.ts`, `calculos.ts`, `verificaciones.ts`, `SelectorColaboradores`, `TablaCantidades` y las clases CSS.
- Sin librerías nuevas (la compresión usa `canvas`, nativo del navegador).
- Se elimina `Reportes.tsx`, porque ya no hay reportes guardados.

## Verificación final
```bash
npm --prefix frontend run lint && npm --prefix frontend run format:check
npm --prefix frontend run test && npm --prefix frontend run build
npm --prefix frontend audit --audit-level=high
gitleaks detect --no-git -v
rg -n "dangerouslySetInnerHTML|href=\{\`/api|guardarDia|subirFoto" frontend/src
```

## Riesgos
- **Pérdida de la semana** al cerrar o recargar la pestaña: así lo decidió Oscar. Se mitiga con el aviso `beforeunload` y el texto fijo.
- **Muchas fotos en un celular:** las fotos comprimidas viven en memoria (unos 300 KB cada una); 100 fotos son unos 30 MB, aceptable.
- **Cada descarga vuelve a subir las fotos:** tres descargas suben tres veces. Es aceptable para el uso semanal; si molesta, en un plan aparte se puede hacer un ZIP con los tres archivos.
- **Nombre del servicio en Render:** si no queda `reportes-servicios-api`, hay que ajustar `connect-src` y `VITE_API_URL`.

## Supuestos y preguntas abiertas
- Supuesto: la sesión dura 8 horas y se pide de nuevo en otra pestaña (`sessionStorage`).
- Sin preguntas abiertas.
