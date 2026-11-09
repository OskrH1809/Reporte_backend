import subprocess
from functools import partial
from pathlib import Path
from tempfile import TemporaryDirectory

from app.errors import PdfError

ejecutar_conversion = partial(
    subprocess.run,
    check=False,
    capture_output=True,
    timeout=120,
)


def generar_pdf(xlsx: bytes) -> bytes:
    with TemporaryDirectory() as temporal:
        directorio = Path(temporal)
        entrada = directorio / "reporte.xlsx"
        salida = directorio / "reporte.pdf"
        perfil = directorio / "perfil"
        entrada.write_bytes(xlsx)
        comando = [
            "/usr/bin/soffice",
            "--headless",
            f"-env:UserInstallation={perfil.resolve().as_uri()}",
            "--convert-to",
            "pdf",
            "--outdir",
            str(directorio),
            str(entrada),
        ]
        try:
            resultado = ejecutar_conversion(comando)
        except (OSError, subprocess.TimeoutExpired) as error:
            raise PdfError("No fue posible generar el PDF") from error
        if resultado.returncode != 0 or not salida.is_file():
            raise PdfError("No fue posible generar el PDF")
        contenido = salida.read_bytes()
        if not contenido.startswith(b"%PDF"):
            raise PdfError("LibreOffice no produjo un PDF válido")
        return contenido
