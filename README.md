# Reportes de Servicios Generales

Aplicacion local para capturar reportes semanales y exportarlos en el formato institucional,
en un libro mejorado y en PDF.

## Uso

1. Copia `.env.example` a `.env` y ajusta solo si es necesario.
2. Ejecuta `make up`.
3. Abre <http://127.0.0.1:8090>.

La aplicacion solo publica el puerto web en `127.0.0.1`.

## Modos

El valor `ALMACENAR` de `.env` decide el modo al iniciar los contenedores:

- `ALMACENAR=true` (predeterminado) guarda los reportes y las fotos en `./data`.
- `ALMACENAR=false` mantiene la semana solo en la pestaña y permite descargar el
  formato actual, el Excel mejorado y el PDF sin guardar el reporte ni sus fotos.
  Descarga los archivos antes de cerrar la pestaña.

### Reabrir una semana

En el modo sin almacenar, usa **Abrir reporte guardado** y selecciona el Excel de
formato actual o el Excel mejorado que descargaste desde la aplicación. El PDF no
sirve para reabrir una semana.

El archivo recupera la captura y las fotos. Si alguien editó el Excel a mano, también
lee las descripciones, el texto de fotos, la observación, las personas asignadas en la
columna «# actividad», las cantidades y las firmas. Revisa los avisos que aparecen al
abrirlo: las horas editadas a mano, las fórmulas y los totales no se leen; las horas se
recalculan.

El Excel incluye una copia oculta para poder reconstruir la semana, por lo que pesa
más que antes: calcula aproximadamente 0.5 MB adicionales por foto.

Los catálogos se guardan en los dos modos. Después de cambiar `ALMACENAR`, ejecuta
`make up` para reiniciar la aplicación con el modo nuevo.

`MAX_EXPORTACION_MB` limita el tamaño total de las fotos enviadas en cada descarga;
su valor predeterminado es 60 MB.

## Despliegue en la nube (Render + Supabase + Vercel)

En la nube la aplicación corre **sin almacenar** (`ALMACENAR=false`) y **con inicio de
sesión** (`AUTENTICACION=true`): solo se guardan los catálogos y los usuarios, en
Postgres de Supabase. El backend no arranca en producción si falta alguna de estas
condiciones. Ningún valor real va en Git: todo se captura en los paneles.

1. **Supabase**: crea un proyecto y copia la cadena de conexión del *Session pooler*
   (IPv4, puerto 5432). La conexión directa es IPv6 y Render no la alcanza. Al
   arrancar, las migraciones crean las tablas con Row-Level Security activado, así
   que la API pública de Supabase no puede leerlas ni modificarlas.
2. **Hash de cada administrador** (en tu equipo):
   `docker compose run --rm api python -m app.cli hash-contrasena`.
   Pide la contraseña dos veces (mínimo 12 caracteres) e imprime solo el hash.
3. **Render**: *New → Blueprint* con este repositorio (`render.yaml`). Captura:
   - `DATABASE_URL`: la cadena del paso 1.
   - `ADMINS_SEMILLA`: `[{"correo":"tu@correo","contrasena_hash":"$argon2id$..."}]`.
     Las semillas crean estos administradores al arrancar; nunca cambian una
     cuenta que ya existe. Para agregar otro, súmalo a la lista y reinicia.
   - `CORS_ORIGINS`: de momento cualquier valor `https://…`; se corrige en el paso 5.
   `JWT_SECRETO` lo genera Render.
4. **Vercel**: importa el repositorio con *Root Directory* `frontend` (Vite,
   `npm run build`, salida `dist`) y define `VITE_API_URL` con la URL de Render
   (`https://<servicio>.onrender.com`). Si Render asignó un nombre distinto de
   `reportes-servicios-api`, cambia también `connect-src` en `frontend/vercel.json`.
5. Pon la URL de Vercel en `CORS_ORIGINS` de Render y reinicia el servicio.

Límites del plan gratuito:

- Render se duerme tras 15 minutos sin uso: la primera carga tarda cerca de un
  minuto (la pantalla de inicio de sesión lo avisa).
- Render tiene 512 MB de memoria. Medido con fotos de 1600 px (~390 KB): 20 fotos
  por semana → pico de 349 MB; 30 fotos → 441 MB. Mantente por debajo de unas 30
  fotos por semana.
- Supabase se pausa tras 7 días sin uso; se reactiva desde su panel.
- La sesión dura 8 horas. Si vence mientras capturas, aparece el inicio de sesión
  encima y la semana no se pierde.

## Verificacion

`make check` ejecuta migraciones, lint, formato, pruebas y auditorias de seguridad.
