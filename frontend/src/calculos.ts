import type { Actividad } from "./api/reportes";

export function calcularHoras(
  actividades: Actividad[],
  jornada: number,
): Actividad[] {
  const resultado = actividades.map((actividad) => ({
    ...actividad,
    asignaciones: actividad.asignaciones.map((asignacion) => ({
      ...asignacion,
    })),
  }));
  const porColaborador = new Map<number, Actividad["asignaciones"]>();
  for (const actividad of resultado) {
    for (const asignacion of actividad.asignaciones) {
      const asignaciones = porColaborador.get(asignacion.colaborador_id) ?? [];
      asignaciones.push(asignacion);
      porColaborador.set(asignacion.colaborador_id, asignaciones);
    }
  }
  for (const asignaciones of porColaborador.values()) {
    const manuales = asignaciones.filter((item) => item.horas_manual);
    const automaticas = asignaciones.filter((item) => !item.horas_manual);
    const usadas = manuales.reduce(
      (total, item) => total + (item.horas ?? 0),
      0,
    );
    const horas = automaticas.length
      ? Math.round((Math.max(jornada - usadas, 0) / automaticas.length) * 100) /
        100
      : 0;
    for (const asignacion of automaticas) asignacion.horas = horas;
  }
  return resultado;
}
