from app.models import Actividad, Asignacion, Colaborador, Dia
from app.services.calculos import jornada_dia, recalcular_horas, totales_dia


def _dia_con_asignaciones(*asignaciones: tuple[str, float, bool]) -> Dia:
    dia = Dia(dia_semana=0)
    colaborador = Colaborador(id=1, nombre="Persona sintética", orden=1)
    actividades: dict[str, Actividad] = {}
    for letra, horas, manual in asignaciones:
        actividad = actividades.setdefault(letra, Actividad(letra=letra, descripcion="Sintética"))
        actividad.asignaciones.append(
            Asignacion(
                colaborador_id=1,
                colaborador=colaborador,
                horas=horas,
                horas_manual=manual,
            )
        )
    dia.actividades = list(actividades.values())
    return dia


def test_reparto_automatico_en_dos_actividades() -> None:
    dia = _dia_con_asignaciones(("A", 0, False), ("B", 0, False))

    recalcular_horas(dia, 8)

    horas = [item.horas for actividad in dia.actividades for item in actividad.asignaciones]
    assert horas == [4, 4]


def test_horas_manuales_reservan_el_resto() -> None:
    dia = _dia_con_asignaciones(("A", 6, True), ("B", 0, False))

    recalcular_horas(dia, 8)

    horas = [item.horas for actividad in dia.actividades for item in actividad.asignaciones]
    assert horas == [6, 2]


def test_sabado_reparte_cinco_horas() -> None:
    dia = _dia_con_asignaciones(("A", 0, False), ("B", 0, False))

    recalcular_horas(dia, 5)

    horas = [item.horas for actividad in dia.actividades for item in actividad.asignaciones]
    assert horas == [2.5, 2.5]


def test_jornada_dia_usa_la_configuracion() -> None:
    assert jornada_dia(Dia(dia_semana=0)) == 8
    assert jornada_dia(Dia(dia_semana=5)) == 5


def test_exceso_manual_genera_advertencia() -> None:
    dia = _dia_con_asignaciones(("A", 9, True))

    personas, horas, actividades, advertencias = totales_dia(dia, 8)

    assert (personas, horas, actividades) == (1, 9, 1)
    assert advertencias == ["Persona sintética supera la jornada de 8 horas"]
