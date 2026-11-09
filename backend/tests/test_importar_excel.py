import json
from io import BytesIO

import pytest
from faker import Faker
from openpyxl import Workbook, load_workbook
from PIL import Image
from sqlalchemy.orm import Session

from app.errors import InvalidFileError
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


def test_formato_sin_respaldo_recupera_campos_y_fotos(session: Session, faker: Faker) -> None:
    catalogos = _catalogos(session, faker)
    datos = _datos(catalogos)
    reporte = armar_reporte(datos, [_foto()], session)
    contenido = generar_formato(reporte, [catalogos[0], catalogos[1]], [catalogos[2]])

    importacion = leer_excel(contenido, session)
    lunes = importacion.datos.dias[0]

    assert importacion.origen == "formato"
    assert lunes.actividades[0].letra == "A"
    assert lunes.actividades[0].descripcion == "Descripción original"
    assert lunes.actividades[0].asignaciones[0].colaborador_id == catalogos[0].id
    assert lunes.herramientas[0].cantidad == 2
    assert lunes.observacion == "Observación original"
    assert importacion.datos.elaborado_por_id == catalogos[4].id
    assert importacion.datos.revisado_por_id == catalogos[5].id
    assert lunes.fotos[0].espacio == "A"
    assert len(importacion.contenidos) == 1
    assert any("materiales" in aviso for aviso in importacion.avisos)


def test_formato_sin_respaldo_avisa_colaborador_desconocido(session: Session, faker: Faker) -> None:
    catalogos = _catalogos(session, faker)
    datos = _datos(catalogos)
    reporte = armar_reporte(datos, [_foto()], session)
    contenido = generar_formato(reporte, [catalogos[0], catalogos[1]], [catalogos[2]])
    libro = load_workbook(BytesIO(contenido))
    libro["Lunes"]["B10"] = faker.unique.name()
    salida = BytesIO()
    libro.save(salida)

    importacion = leer_excel(salida.getvalue(), session)

    assert importacion.datos.dias[0].actividades[0].asignaciones == []
    assert any("No se encontró el colaborador" in aviso for aviso in importacion.avisos)


def test_formato_sin_respaldo_lee_bandas_hasta_j(session: Session, faker: Faker) -> None:
    catalogos = _catalogos(session, faker)
    datos_dict = _datos(catalogos).model_dump(mode="json")
    datos_dict["dias"][0]["actividades"] = [
        {
            "letra": letra,
            "descripcion": f"Descripción {letra}",
            "asignaciones": [],
        }
        for letra in "ABCDEFGHIJ"
    ]
    datos = ReporteExportar.model_validate(datos_dict)
    reporte = armar_reporte(datos, [_foto()], session)
    contenido = generar_formato(reporte, [catalogos[0], catalogos[1]], [catalogos[2]])

    importacion = leer_excel(contenido, session)

    assert [item.letra for item in importacion.datos.dias[0].actividades] == list("ABCDEFGHIJ")
    assert importacion.datos.dias[0].actividades[-1].descripcion == "Descripción J"


def test_libro_vacio_no_se_reconoce(session: Session) -> None:
    libro = Workbook()
    salida = BytesIO()
    libro.save(salida)

    with pytest.raises(InvalidFileError, match="no tiene datos para reabrir"):
        leer_excel(salida.getvalue(), session)
