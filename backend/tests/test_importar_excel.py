import json
from io import BytesIO

from faker import Faker
from openpyxl import load_workbook
from PIL import Image
from sqlalchemy.orm import Session

from app.models import Colaborador, Firmante, Herramienta, Material
from app.schemas.exportar import ReporteExportar
from app.services.excel_formato import generar_formato
from app.services.excel_mejorado import generar_mejorado
from app.services.importar_excel import leer_excel
from app.services.reporte_memoria import armar_reporte
from app.services.respaldo_excel import RespaldoSemana


def _foto() -> bytes:
    salida = BytesIO()
    Image.new("RGB", (40, 30), "purple").save(salida, "JPEG")
    return salida.getvalue()


def _catalogos(session: Session, faker: Faker):
    colaborador = Colaborador(nombre=faker.unique.name(), orden=970)
    otro = Colaborador(nombre=faker.unique.name(), orden=971)
    herramienta = Herramienta(nombre=faker.unique.word(), orden=970)
    material = Material(nombre=faker.unique.word(), unidad="u", orden=970)
    elabora = Firmante(nombre=faker.unique.name(), tipo="elabora")
    revisa = Firmante(nombre=faker.unique.name(), tipo="revisa")
    session.add_all([colaborador, otro, herramienta, material, elabora, revisa])
    session.flush()
    return colaborador, otro, herramienta, material, elabora, revisa


def _datos(catalogos) -> ReporteExportar:
    colaborador, _otro, herramienta, material, elabora, revisa = catalogos
    return ReporteExportar.model_validate(
        {
            "anio": 2026,
            "semana": 45,
            "elaborado_por_id": elabora.id,
            "revisado_por_id": revisa.id,
            "dias": [
                {
                    "dia_semana": dia,
                    "observacion": "Observación original",
                    "texto_fotos": "Evidencia original",
                    "actividades": [
                        {
                            "letra": "A",
                            "descripcion": "Descripción original",
                            "asignaciones": [{"colaborador_id": colaborador.id}],
                        }
                    ]
                    if dia == 0
                    else [],
                    "herramientas": [{"herramienta_id": herramienta.id, "cantidad": 2}]
                    if dia == 0
                    else [],
                    "materiales": [{"material_id": material.id, "cantidad": 3}] if dia == 0 else [],
                    "fotos": [{"indice": 0, "espacio": "A"}] if dia == 0 else [],
                }
                for dia in range(6)
            ],
        }
    )


def _excel(session: Session, faker: Faker, *, mejorado: bool = False):
    catalogos = _catalogos(session, faker)
    datos = _datos(catalogos)
    contenidos = [_foto()]
    reporte = armar_reporte(datos, contenidos, session)
    respaldo = RespaldoSemana(datos=datos, contenidos=contenidos)
    if mejorado:
        contenido = generar_mejorado(
            reporte, [catalogos[0], catalogos[1]], [catalogos[2]], [catalogos[3]], respaldo
        )
    else:
        contenido = generar_formato(reporte, [catalogos[0], catalogos[1]], [catalogos[2]], respaldo)
    return contenido, datos, contenidos, catalogos


def _editar(contenido: bytes, cambios: dict[str, object]) -> bytes:
    libro = load_workbook(BytesIO(contenido), data_only=False)
    respaldo = libro["_respaldo"]
    mapa = json.loads("".join(celda.value for celda in respaldo[3] if celda.value is not None))
    for clave, valor in cambios.items():
        hoja, celda = mapa[clave][0].rsplit("!", 1)
        libro[hoja][celda] = valor
    salida = BytesIO()
    libro.save(salida)
    return salida.getvalue()


def test_ida_y_vuelta_con_respaldo_conserva_datos_y_fotos(session: Session, faker: Faker) -> None:
    contenido, datos, fotos, _catalogos_creados = _excel(session, faker)

    importacion = leer_excel(contenido, session)

    assert importacion.origen == "respaldo"
    assert importacion.datos == datos
    assert importacion.contenidos == fotos
    assert importacion.avisos == []


def test_toma_descripcion_literal_y_cambios_de_asignacion_y_cantidad(
    session: Session, faker: Faker
) -> None:
    contenido, _datos_originales, _fotos, catalogos = _excel(session, faker)
    colaborador, _otro, herramienta, *_resto = catalogos
    editado = _editar(
        contenido,
        {
            "d0.act.A.descripcion": "=SUMA(A1:A2)",
            f"d0.colab.{colaborador.id}.letras": "A, C",
            f"d0.herr.{herramienta.id}.cantidad": 0,
        },
    )

    importacion = leer_excel(editado, session)
    lunes = importacion.datos.dias[0]

    assert lunes.actividades[0].descripcion == "=SUMA(A1:A2)"
    actividad_c = next(item for item in lunes.actividades if item.letra == "C")
    assert actividad_c.asignaciones[0].colaborador_id == colaborador.id
    assert actividad_c.asignaciones[0].horas == 4
    assert lunes.herramientas == []
    assert any("descripción editada" in aviso for aviso in importacion.avisos)


def test_colaborador_desconocido_genera_aviso_y_conserva_original(
    session: Session, faker: Faker
) -> None:
    contenido, _datos_originales, _fotos, catalogos = _excel(session, faker)
    colaborador = catalogos[0]
    editado = _editar(
        contenido,
        {f"d0.colab.{colaborador.id}.nombre": faker.unique.name()},
    )

    importacion = leer_excel(editado, session)

    assert importacion.datos.dias[0].actividades[0].asignaciones[0].colaborador_id == colaborador.id
    assert any("no se encontró el colaborador" in aviso for aviso in importacion.avisos)


def test_mejorado_toma_descripcion_cantidades_y_observacion(session: Session, faker: Faker) -> None:
    contenido, _datos_originales, _fotos, catalogos = _excel(session, faker, mejorado=True)
    herramienta, material = catalogos[2], catalogos[3]
    editado = _editar(
        contenido,
        {
            "d0.act.A.descripcion": "Descripción mejorada editada",
            f"d0.herr.{herramienta.id}.cantidad": 7,
            f"d0.mat.{material.id}.cantidad": 9,
            "d0.observacion": "Observación mejorada editada",
        },
    )

    importacion = leer_excel(editado, session)
    lunes = importacion.datos.dias[0]

    assert lunes.actividades[0].descripcion == "Descripción mejorada editada"
    assert lunes.herramientas[0].cantidad == 7
    assert lunes.materiales[0].cantidad == 9
    assert lunes.observacion == "Observación mejorada editada"
