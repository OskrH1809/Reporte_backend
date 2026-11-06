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
export const listarReportes = () => apiRequest<Reporte[]>("/reportes");
export const crearReporte = (anio: number, semana: number) =>
  apiRequest<Reporte>("/reportes", {
    method: "POST",
    body: JSON.stringify({ anio, semana }),
  });
export const eliminarReporte = (id: number) =>
  apiRequest<void>(`/reportes/${id}`, { method: "DELETE" });
