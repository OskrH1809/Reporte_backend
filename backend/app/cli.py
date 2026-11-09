"""Utilidades de línea de comandos.

    python -m app.cli hash-contrasena

Pide la contraseña sin mostrarla e imprime solo su hash argon2, para pegarlo en
ADMINS_SEMILLA. Nunca recibe la contraseña como argumento (quedaría en el historial).
"""

import argparse
import sys
from collections.abc import Callable
from getpass import getpass

from app.services.auth import hashear

LARGO_MINIMO = 12


def pedir_contrasena(leer: Callable[[str], str] = getpass) -> str:
    primera = leer("Contraseña: ")
    if len(primera) < LARGO_MINIMO:
        raise ValueError(f"La contraseña debe tener al menos {LARGO_MINIMO} caracteres")
    if leer("Repite la contraseña: ") != primera:
        raise ValueError("Las contraseñas no coinciden")
    return primera


def main(argumentos: list[str] | None = None, leer: Callable[[str], str] = getpass) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    subcomandos = parser.add_subparsers(dest="comando", required=True)
    subcomandos.add_parser("hash-contrasena", help="Genera el hash argon2 de una contraseña")
    parser.parse_args(argumentos)
    try:
        contrasena = pedir_contrasena(leer)
    except ValueError as error:
        print(error, file=sys.stderr)
        return 1
    print(hashear(contrasena))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
