# Reportes de Servicios Generales

Aplicacion local para capturar reportes semanales y exportarlos en el formato institucional,
en un libro mejorado y en PDF.

## Uso

1. Copia `.env.example` a `.env` y ajusta solo si es necesario.
2. Ejecuta `make up`.
3. Abre <http://127.0.0.1:8090>.

Los datos se guardan en `./data/app.db`. La aplicacion solo publica el puerto web en
`127.0.0.1`.

## Verificacion

`make check` ejecuta migraciones, lint, formato, pruebas y auditorias de seguridad.
