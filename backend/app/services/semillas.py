import json
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import AdminSemilla, get_settings
from app.models import Colaborador, Firmante, Herramienta, Material, Usuario

RUTA_SEMILLAS = Path(__file__).resolve().parents[1] / "seeds" / "catalogos.json"


def cargar_semillas(session: Session) -> None:
    datos = json.loads(RUTA_SEMILLAS.read_text(encoding="utf-8"))
    modelos_simples = {
        "colaboradores": Colaborador,
        "herramientas": Herramienta,
    }
    for clave, modelo in modelos_simples.items():
        if session.scalar(select(func.count()).select_from(modelo)) == 0:
            session.add_all(
                modelo(nombre=nombre, orden=orden)
                for orden, nombre in enumerate(datos[clave], start=1)
            )

    if session.scalar(select(func.count()).select_from(Material)) == 0:
        session.add_all(
            Material(nombre=item["nombre"], unidad=item["unidad"], orden=orden)
            for orden, item in enumerate(datos["materiales"], start=1)
        )
    if session.scalar(select(func.count()).select_from(Firmante)) == 0:
        session.add_all(Firmante(**item) for item in datos["firmantes"])
    cargar_usuarios_semilla(session, get_settings().admins_semilla)
    session.commit()


def cargar_usuarios_semilla(session: Session, admins: list[AdminSemilla]) -> int:
    """Crea los administradores que aún no existen; nunca modifica cuentas existentes."""
    existentes = set(session.scalars(select(Usuario.correo)))
    creados = 0
    for admin in admins:
        if admin.correo in existentes:
            continue
        session.add(
            Usuario(
                correo=admin.correo,
                contrasena_hash=admin.contrasena_hash.get_secret_value(),
                activo=True,
            )
        )
        existentes.add(admin.correo)
        creados += 1
    session.flush()
    return creados
