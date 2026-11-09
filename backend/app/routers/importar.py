from io import BytesIO
from pathlib import PurePosixPath
from typing import Annotated
from zipfile import BadZipFile, ZipFile

from fastapi import APIRouter, Depends, File, Request, UploadFile
from sqlalchemy.orm import Session

from app.config import Settings
from app.db import get_db
from app.errors import FileTooLargeError, InvalidFileError
from app.schemas.exportar import ImportacionRead
from app.services.importar_excel import leer_excel

DatabaseSession = Annotated[Session, Depends(get_db)]
router = APIRouter(prefix="/api", tags=["importacion"])
MAX_ENTRADAS_ZIP = 2_000
MAX_DESCOMPRIMIDO = 300 * 1024 * 1024


def _validar_zip(contenido: bytes) -> None:
    if not contenido.startswith(b"PK\x03\x04"):
        raise InvalidFileError("Archivo de Excel no válido")
    try:
        with ZipFile(BytesIO(contenido)) as archivo:
            entradas = archivo.infolist()
            if len(entradas) > MAX_ENTRADAS_ZIP:
                raise InvalidFileError("Archivo de Excel no válido")
            if sum(entrada.file_size for entrada in entradas) > MAX_DESCOMPRIMIDO:
                raise InvalidFileError("Archivo de Excel no válido")
            for entrada in entradas:
                ruta = PurePosixPath(entrada.filename.replace("\\", "/"))
                if ruta.is_absolute() or ".." in ruta.parts:
                    raise InvalidFileError("Archivo de Excel no válido")
    except (BadZipFile, OSError, ValueError) as error:
        raise InvalidFileError("Archivo de Excel no válido") from error


@router.post("/importar", response_model=ImportacionRead)
def importar_excel(
    request: Request,
    session: DatabaseSession,
    archivo: Annotated[UploadFile, File()],
) -> ImportacionRead:
    settings: Settings = request.app.state.settings
    limite = settings.max_exportacion_mb * 1024 * 1024
    contenido = archivo.file.read(limite + 1)
    if len(contenido) > limite:
        raise FileTooLargeError(f"El archivo supera el máximo de {settings.max_exportacion_mb} MB")
    _validar_zip(contenido)
    return ImportacionRead.desde_importacion(leer_excel(contenido, session))
