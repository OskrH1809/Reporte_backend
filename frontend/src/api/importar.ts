import type { Actividad, Cantidad, Letra } from "./reportes";
import { apiRequest } from "./client";

export interface DiaImportado {
  dia_semana: number;
  observacion: string;
  texto_fotos: string;
  actividades: Actividad[];
  herramientas: Cantidad[];
  materiales: Cantidad[];
  fotos: Array<{ indice: number; espacio: Letra | "AD" }>;
}

export interface ImportacionRead {
  datos: {
    anio: number;
    semana: number;
    elaborado_por_id: number | null;
    revisado_por_id: number | null;
    dias: DiaImportado[];
  };
  fotos: Array<{
    indice: number;
    espacio: Letra | "AD";
    dia_semana: number;
    contenido_base64: string;
  }>;
  avisos: string[];
  origen: "respaldo" | "formato";
}

export function importarExcel(archivo: File): Promise<ImportacionRead> {
  const formulario = new FormData();
  formulario.set("archivo", archivo);
  return apiRequest<ImportacionRead>("/importar", {
    method: "POST",
    body: formulario,
  });
}
