from io import BytesIO
from pathlib import Path
from uuid import uuid4

from PIL import Image, ImageOps, UnidentifiedImageError

from app.errors import FileTooLargeError, InvalidFileError

FOTOS_DIR = Path("/data/fotos")
FORMATOS = {"JPEG", "PNG", "WEBP"}
MAX_LADO = 1600


def normalizar_foto(contenido: bytes, max_mb: int) -> bytes:
    if len(contenido) > max_mb * 1024 * 1024:
        raise FileTooLargeError(f"La foto supera el máximo de {max_mb} MB")
    try:
        with Image.open(BytesIO(contenido)) as original:
            if original.format not in FORMATOS:
                raise InvalidFileError("El archivo debe ser JPEG, PNG o WebP")
            original.verify()
        with Image.open(BytesIO(contenido)) as original:
            imagen = ImageOps.exif_transpose(original)
            imagen.thumbnail((MAX_LADO, MAX_LADO), Image.Resampling.LANCZOS)
            if imagen.mode != "RGB":
                fondo = Image.new("RGB", imagen.size, "white")
                if "A" in imagen.getbands():
                    fondo.paste(imagen, mask=imagen.getchannel("A"))
                else:
                    fondo.paste(imagen)
                imagen = fondo
            salida = BytesIO()
            imagen.save(salida, "JPEG", quality=85, optimize=True)
            return salida.getvalue()
    except (UnidentifiedImageError, OSError, ValueError) as error:
        raise InvalidFileError("El archivo no es una imagen válida") from error


def procesar_foto(contenido: bytes, max_mb: int) -> str:
    normalizada = normalizar_foto(contenido, max_mb)
    FOTOS_DIR.mkdir(parents=True, exist_ok=True)
    nombre = f"{uuid4()}.jpg"
    (FOTOS_DIR / nombre).write_bytes(normalizada)
    return nombre


def eliminar_archivo(nombre: str) -> None:
    ruta = FOTOS_DIR / Path(nombre).name
    ruta.unlink(missing_ok=True)
