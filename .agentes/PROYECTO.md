---
nombre: Proyecto_Tania
perfil: personal
estado: nuevo
---

# PROYECTO — <nombre>

> Decisiones fijas del proyecto. Claude y Codex las siguen en cada plan. Cambiarlas requiere un plan dedicado.

## Qué es
- **Problema que resuelve:** 
- **Usuarios:** solo yo / usuarios con cuenta / público
- **Alcance de la v1 (MVP):** 3–5 funcionalidades, nada más

## Stack
| Capa | Elección | Versión |
|---|---|---|
| Backend | | |
| Base de datos | | |
| ORM / migraciones | | |
| Validación | | |
| Autenticación | | |
| Frontend | | |
| Pruebas | | |
| Formato / lint | | |
| Despliegue | | |

## Estructura de carpetas
```
(árbol acordado)
```

## Convenciones
- Idioma del código: inglés / español · Idioma de la UI: 
- Formato de error de la API: `{"detail": "...", "code": "..."}`
- Fechas: UTC en BD, ISO-8601 en la API
- IDs: entero autoincremental / UUID
- Borrado: físico / lógico (`deleted_at`)

## Seguridad base (medidas de `SEGURIDAD.md` resueltas a nivel proyecto)
| # | Medida | Decisión |
|---|---|---|
| 1–2 | Secretos | `.env` + `.env.example`, gitleaks en pre-commit |
| 6 | Autenticación | |
| 9 | Cookies / tokens | |
| 10 | Hash de contraseñas | |
| 11 | Rate limiting | |
| 18–19 | Headers / HTTPS | |
| 20 | Dependencias | |

## Piezas de referencia (se llenan tras el plan de esqueleto)
| Tipo | Archivo |
|---|---|
| Endpoint | |
| Modelo + migración | |
| Servicio | |
| Componente UI | |
| Prueba de API | |
| Prueba unitaria | |

## Comandos
```bash
# instalar dependencias
# levantar en local
# lint + formato
# pruebas
# escaneos de seguridad
```
