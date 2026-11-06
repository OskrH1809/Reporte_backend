from collections import defaultdict

from app.models import Dia


def recalcular_horas(dia: Dia, jornada: float) -> None:
    por_colaborador = defaultdict(list)
    for actividad in dia.actividades:
        for asignacion in actividad.asignaciones:
            por_colaborador[asignacion.colaborador_id].append(asignacion)

    for asignaciones in por_colaborador.values():
        manuales = [item for item in asignaciones if item.horas_manual]
        automaticas = [item for item in asignaciones if not item.horas_manual]
        restante = max(jornada - sum(item.horas for item in manuales), 0)
        horas_automaticas = restante / len(automaticas) if automaticas else 0
        for asignacion in automaticas:
            asignacion.horas = round(horas_automaticas, 2)


def totales_dia(dia: Dia, jornada: float) -> tuple[int, float, int, list[str]]:
    colaboradores: dict[int, float] = defaultdict(float)
    horas_hombre = 0.0
    numero_actividades = 0
    for actividad in dia.actividades:
        if actividad.asignaciones:
            numero_actividades += 1
        for asignacion in actividad.asignaciones:
            horas_hombre += asignacion.horas
            colaboradores[asignacion.colaborador_id] += asignacion.horas
    advertencias = [
        f"El colaborador {colaborador_id} supera la jornada de {jornada:g} horas"
        for colaborador_id, horas in colaboradores.items()
        if horas > jornada
    ]
    return len(colaboradores), round(horas_hombre, 2), numero_actividades, advertencias
