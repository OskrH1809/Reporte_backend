import type { DiaInput, Letra } from "./api/reportes";
import { serializarDia } from "./api/reportes";
import type { ImportacionRead } from "./api/importar";
import { armarActividades } from "./actividades";

export const TEXTO_FOTOS_PREDETERMINADO =
  "Fotos antes y después de la actividad realizada";

export interface FotoLocal {
  id: string;
  espacio: Letra | "AD";
  archivo: Blob;
  url: string;
  nombre_original: string;
}

export type DiaLocal = DiaInput & {
  dia_semana: number;
  fecha: string;
  fotos: FotoLocal[];
};

export interface SemanaLocal {
  anio: number;
  semana: number;
  elaborado_por_id: number | null;
  revisado_por_id: number | null;
  dias: DiaLocal[];
}

const DIA_MS = 24 * 60 * 60 * 1000;

export function semanaISO(fecha: Date): { anio: number; semana: number } {
  const actual = new Date(
    Date.UTC(fecha.getFullYear(), fecha.getMonth(), fecha.getDate()),
  );
  const dia = actual.getUTCDay() || 7;
  actual.setUTCDate(actual.getUTCDate() + 4 - dia);
  const anio = actual.getUTCFullYear();
  const inicio = new Date(Date.UTC(anio, 0, 1));
  const semana = Math.ceil(
    (Number(actual) - Number(inicio) + DIA_MS) / DIA_MS / 7,
  );
  return { anio, semana };
}

function lunesISO(anio: number, semana: number): Date {
  const cuatroEnero = new Date(Date.UTC(anio, 0, 4));
  const dia = cuatroEnero.getUTCDay() || 7;
  const lunes = new Date(cuatroEnero);
  lunes.setUTCDate(cuatroEnero.getUTCDate() - dia + 1 + (semana - 1) * 7);
  return lunes;
}

export function crearSemana(anio: number, semana: number): SemanaLocal {
  const lunes = lunesISO(anio, semana);
  return {
    anio,
    semana,
    elaborado_por_id: null,
    revisado_por_id: null,
    dias: Array.from({ length: 6 }, (_valor, dia_semana) => ({
      dia_semana,
      fecha: new Date(Number(lunes) + dia_semana * DIA_MS)
        .toISOString()
        .slice(0, 10),
      observacion: "",
      texto_fotos: TEXTO_FOTOS_PREDETERMINADO,
      actividades: armarActividades([]),
      herramientas: [],
      materiales: [],
      fotos: [],
    })),
  };
}

function blobBase64(contenido: string): Blob {
  const binario = atob(contenido);
  const bytes = Uint8Array.from(binario, (caracter) => caracter.charCodeAt(0));
  return new Blob([bytes], { type: "image/jpeg" });
}

export function semanaDesdeImportacion(
  importacion: ImportacionRead,
): SemanaLocal {
  const base = crearSemana(importacion.datos.anio, importacion.datos.semana);
  return {
    ...base,
    elaborado_por_id: importacion.datos.elaborado_por_id,
    revisado_por_id: importacion.datos.revisado_por_id,
    dias: base.dias.map((diaBase) => {
      const dia = importacion.datos.dias.find(
        (item) => item.dia_semana === diaBase.dia_semana,
      );
      if (!dia) return diaBase;
      const fotos = importacion.fotos
        .filter((foto) => foto.dia_semana === dia.dia_semana)
        .map((foto) => {
          const archivo = blobBase64(foto.contenido_base64);
          return {
            id: `foto-importada-${foto.indice}`,
            espacio: foto.espacio,
            archivo,
            url: URL.createObjectURL(archivo),
            nombre_original: `foto-importada-${foto.indice + 1}.jpg`,
          };
        });
      return {
        ...diaBase,
        observacion: dia.observacion,
        texto_fotos: dia.texto_fotos,
        actividades: armarActividades(dia.actividades, fotos),
        herramientas: dia.herramientas,
        materiales: dia.materiales,
        fotos,
      };
    }),
  };
}

export function armarFormData(semana: SemanaLocal): FormData {
  const formulario = new FormData();
  let indice = 0;
  const dias = semana.dias.map((dia) => {
    const fotos = dia.fotos.map((foto) => {
      formulario.append("fotos", foto.archivo, foto.nombre_original);
      return { indice: indice++, espacio: foto.espacio };
    });
    return {
      dia_semana: dia.dia_semana,
      ...serializarDia({
        ...dia,
        actividades: dia.actividades.filter(
          (actividad) => actividad.descripcion || actividad.asignaciones.length,
        ),
      }),
      fotos,
    };
  });
  formulario.set(
    "datos",
    JSON.stringify({
      anio: semana.anio,
      semana: semana.semana,
      elaborado_por_id: semana.elaborado_por_id,
      revisado_por_id: semana.revisado_por_id,
      dias,
    }),
  );
  return formulario;
}

export async function comprimirFoto(archivo: File): Promise<Blob> {
  try {
    const imagen = await createImageBitmap(archivo);
    const escala = Math.min(1, 1600 / Math.max(imagen.width, imagen.height));
    const canvas = document.createElement("canvas");
    canvas.width = Math.max(1, Math.round(imagen.width * escala));
    canvas.height = Math.max(1, Math.round(imagen.height * escala));
    const contexto = canvas.getContext("2d");
    if (!contexto) throw new Error("Canvas no disponible");
    contexto.drawImage(imagen, 0, 0, canvas.width, canvas.height);
    imagen.close();
    const resultado = await new Promise<Blob | null>((resolve) =>
      canvas.toBlob(resolve, "image/jpeg", 0.82),
    );
    return resultado ?? archivo;
  } catch {
    return archivo;
  }
}
