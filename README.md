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
más que antes: calcula aproximadamente 0.4 MB adicionales por foto.

Los catálogos se guardan en los dos modos. Después de cambiar `ALMACENAR`, ejecuta
`make up` para reiniciar la aplicación con el modo nuevo.

`MAX_EXPORTACION_MB` limita el tamaño total de las fotos enviadas en cada descarga;
su valor predeterminado es 60 MB. Como referencia, generar un PDF con unas 20 fotos
de 1600 px produce un pico aproximado de 316 MB de memoria.

## Verificacion

`make check` ejecuta migraciones, lint, formato, pruebas y auditorias de seguridad.
