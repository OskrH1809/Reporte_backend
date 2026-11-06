import { apiRequest } from "./client";

export interface Reporte {
  id: number;
  anio: number;
  semana: number;
  codigo: string;
  fecha_inicio: string;
  fecha_fin: string;
  elaborado_por_id: number | null;
  revisado_por_id: number | null;
  horas_hombre: number;
}
export interface Asignacion {
  id?: number;
  colaborador_id: number;
  colaborador_nombre?: string;
  horas?: number;
  horas_manual: boolean;
}
export interface Actividad {
  id?: number;
  letra: "A" | "B" | "C";
  descripcion: string;
  asignaciones: Asignacion[];
  personas?: number;
  horas_hombre?: number;
}
export interface Cantidad {
  herramienta_id?: number;
  material_id?: number;
  nombre?: string;
  unidad?: string;
  cantidad: number;
}
export interface Foto {
  id: number;
  espacio: "A" | "B" | "C" | "AD";
  orden: number;
  nombre_original: string;
  url: string;
}
export interface Dia {
  id: number;
  dia_semana: number;
  fecha: string;
  observacion: string;
  texto_fotos: string;
  actividades: Actividad[];
  herramientas: Cantidad[];
  materiales: Cantidad[];
  fotos: Foto[];
  personas: number;
  horas_hombre: number;
  numero_actividades: number;
  advertencias: string[];
}
export type DiaInput = Pick<
  Dia,
  "observacion" | "texto_fotos" | "actividades" | "herramientas" | "materiales"
>;
export const listarReportes = () => apiRequest<Reporte[]>("/reportes");
export const crearReporte = (anio: number, semana: number) =>
  apiRequest<Reporte>("/reportes", {
    method: "POST",
    body: JSON.stringify({ anio, semana }),
  });
export const eliminarReporte = (id: number) =>
  apiRequest<void>(`/reportes/${id}`, { method: "DELETE" });
export const verReporte = (id: number) =>
  apiRequest<Reporte>(`/reportes/${id}`);
export const editarReporte = (
  id: number,
  input: { elaborado_por_id?: number | null; revisado_por_id?: number | null },
) =>
  apiRequest<Reporte>(`/reportes/${id}`, {
    method: "PATCH",
    body: JSON.stringify(input),
  });
export const verDia = (id: number, dia: number) =>
  apiRequest<Dia>(`/reportes/${id}/dias/${dia}`);
export const guardarDia = (id: number, dia: number, input: DiaInput) =>
  apiRequest<Dia>(`/reportes/${id}/dias/${dia}`, {
    method: "PUT",
    body: JSON.stringify(input),
  });
export async function subirFoto(
  id: number,
  dia: number,
  espacio: Foto["espacio"],
  archivo: File,
): Promise<Foto> {
  const datos = new FormData();
  datos.set("espacio", espacio);
  datos.set("archivo", archivo);
  return apiRequest<Foto>(`/reportes/${id}/dias/${dia}/fotos`, {
    method: "POST",
    body: datos,
  });
}
export async function subirFotos(
  id: number,
  dia: number,
  espacio: Foto["espacio"],
  archivos: File[],
): Promise<void> {
  for (const archivo of archivos) await subirFoto(id, dia, espacio, archivo);
}
export const eliminarFoto = (id: number) =>
  apiRequest<void>(`/fotos/${id}`, { method: "DELETE" });
