from io import BytesIO

from faker import Faker
from openpyxl import load_workbook
from sqlalchemy.orm import Session

from app.models import Actividad, Asignacion, Colaborador, Dia, Herramienta, Reporte
from app.services.excel_formato import generar_formato


def _reporte(session: Session, faker: Faker, semana: int = 43) -> Reporte:
    colaboradores = [
        Colaborador(nombre=faker.name(), orden=-1000 - semana + indice) for indice in range(1, 3)
    ]
    herramienta = Herramienta(nombre=faker.word(), orden=1)
    reporte = Reporte(anio=2026, semana=semana)
    reporte.dias = [
        Dia(dia_semana=indice, fecha=faker.date_between(start_date="+1d", end_date="+30d"))
        for indice in range(6)
    ]
    reporte.dias[0].actividades = [
        Actividad(
            letra="A",
            descripcion=faker.sentence(),
            asignaciones=[Asignacion(colaborador=colaboradores[0], horas=4, horas_manual=False)],
        ),
        Actividad(
            letra="B",
            descripcion=faker.sentence(),
            asignaciones=[Asignacion(colaborador=colaboradores[0], horas=4, horas_manual=False)],
        ),
    ]
    session.add_all([*colaboradores, herramienta, reporte])
    session.commit()
    return reporte


def test_formato_tiene_hojas_celdas_y_formulas(session: Session, faker: Faker) -> None:
    reporte = _reporte(session, faker)
    libro = load_workbook(BytesIO(generar_formato(reporte)), data_only=False)

    assert libro.sheetnames == [
        "Lunes",
        "Martes",
        "Miercoles",
        "Jueves",
        "Viernes",
        "Sabado",
        "Datos",
    ]
    lunes = libro["Lunes"]
    assert lunes["I6"].value == 43
    assert lunes["H10"].value == "A, B"
    assert lunes["M11"].value.startswith("=COUNTIF")
    assert lunes["M13"].value == 4
    assert lunes.print_area == "'Lunes'!$A$1:$T$58"
    assert libro["Martes"].print_area == "'Martes'!$A$1:$T$54"
    assert libro["Datos"]["E8"].value == "=+Lunes!M19+Lunes!N19+Lunes!O19"
    assert libro["Datos"]["K8"].value == "=SUM(E8:J8)"


def test_formato_conserva_letra_de_colaborador(session: Session, faker: Faker) -> None:
    reporte = _reporte(session, faker, semana=44)
    libro = load_workbook(BytesIO(generar_formato(reporte)))

    lunes = libro["Lunes"]
    assert "A, B" in [lunes.cell(fila, 8).value for fila in range(10, 23)]
    assert libro["Lunes"]["D26"].value == reporte.dias[0].actividades[0].descripcion
