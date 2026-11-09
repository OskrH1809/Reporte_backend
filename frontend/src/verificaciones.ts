import type { Actividad, Cantidad, Foto } from "./api/reportes";

export interface Verificacion {
  nivel: "error" | "aviso";
  mensaje: string;
  seccion: "actividades" | "herramientas" | "materiales" | "fotos" | "general";
}

interface EntradaVerificacion {
  actividades: Actividad[];
  herramientas: Cantidad[];
  materiales: Cantidad[];
  fotos: Pick<Foto, "espacio">[];
  observacion: string;
  jornada: number;
  nombres: Map<number, string>;
}

const numero = (valor: number) => valor.toLocaleString("es");

export function verificarDia({
  actividades,
  herramientas,
  materiales,
  fotos,
  observacion,
  jornada,
  nombres,
}: EntradaVerificacion): Verificacion[] {
  const verificaciones: Verificacion[] = [];
  const horasPorPersona = new Map<number, number>();

  for (const actividad of actividades) {
    for (const asignacion of actividad.asignaciones) {
      horasPorPersona.set(
        asignacion.colaborador_id,
        (horasPorPersona.get(asignacion.colaborador_id) ?? 0) +
          (Number.isFinite(asignacion.horas) ? (asignacion.horas ?? 0) : 0),
      );
    }
  }

  for (const [colaboradorId, horas] of horasPorPersona) {
    if (horas > jornada) {
      verificaciones.push({
        nivel: "error",
        mensaje: `${nombres.get(colaboradorId) ?? `Colaborador ${colaboradorId}`} suma ${numero(horas)} h; la jornada es de ${numero(jornada)} h.`,
        seccion: "actividades",
      });
    }
  }

  for (const actividad of actividades) {
    for (const asignacion of actividad.asignaciones) {
      if (!Number.isFinite(asignacion.horas) || (asignacion.horas ?? 0) <= 0) {
        verificaciones.push({
          nivel: "error",
          mensaje: `${nombres.get(asignacion.colaborador_id) ?? `Colaborador ${asignacion.colaborador_id}`} no tiene horas en la actividad ${actividad.letra}.`,
          seccion: "actividades",
        });
      }
    }
  }

  for (const actividad of actividades) {
    if (actividad.asignaciones.length > 0 && !actividad.descripcion.trim()) {
      verificaciones.push({
        nivel: "error",
        mensaje: `La actividad ${actividad.letra} tiene personas pero no descripción.`,
        seccion: "actividades",
      });
    }
  }

  for (const [cantidades, seccion] of [
    [herramientas, "herramientas"],
    [materiales, "materiales"],
  ] as const) {
    for (const item of cantidades) {
      if (!Number.isFinite(item.cantidad) || item.cantidad <= 0) {
        verificaciones.push({
          nivel: "error",
          mensaje: `La cantidad de ${item.nombre || "un elemento"} debe ser mayor que 0.`,
          seccion,
        });
      }
    }
  }

  for (const actividad of actividades) {
    if (actividad.descripcion.trim() && actividad.asignaciones.length === 0) {
      verificaciones.push({
        nivel: "aviso",
        mensaje: `La actividad ${actividad.letra} no tiene personas asignadas.`,
        seccion: "actividades",
      });
    }
  }

  for (const [colaboradorId, horas] of horasPorPersona) {
    if (horas < jornada) {
      verificaciones.push({
        nivel: "aviso",
        mensaje: `${nombres.get(colaboradorId) ?? `Colaborador ${colaboradorId}`} suma ${numero(horas)} h de ${numero(jornada)} h.`,
        seccion: "actividades",
      });
    }
  }

  for (const actividad of actividades) {
    if (
      actividad.descripcion.trim() &&
      !fotos.some((foto) => foto.espacio === actividad.letra)
    ) {
      verificaciones.push({
        nivel: "aviso",
        mensaje: `La actividad ${actividad.letra} no tiene fotos.`,
        seccion: "fotos",
      });
    }
  }

  const hayPersonas = actividades.some(
    (actividad) => actividad.asignaciones.length > 0,
  );
  const hayActividad = actividades.some(
    (actividad) =>
      actividad.descripcion.trim() || actividad.asignaciones.length > 0,
  );
  if (!hayActividad && !observacion.trim()) {
    verificaciones.push({
      nivel: "aviso",
      mensaje:
        "Día sin actividades: escribe una observación (por ejemplo, feriado).",
      seccion: "general",
    });
  }

  if (hayPersonas && herramientas.length === 0) {
    verificaciones.push({
      nivel: "aviso",
      mensaje: "No se registraron herramientas.",
      seccion: "herramientas",
    });
  }

  return verificaciones;
}
