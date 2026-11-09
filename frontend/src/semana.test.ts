import { expect, it, vi } from "vitest";

import type { ImportacionRead } from "./api/importar";
import { armarFormData, crearSemana, semanaDesdeImportacion } from "./semana";

it("crea la semana 45 de 2026 de lunes a sábado", () => {
  const semana = crearSemana(2026, 45);

  expect(semana.dias.map((dia) => dia.fecha)).toEqual([
    "2026-11-02",
    "2026-11-03",
    "2026-11-04",
    "2026-11-05",
    "2026-11-06",
    "2026-11-07",
  ]);
});

it("arma datos exactos, filtra actividades vacías e indexa fotos", () => {
  const semana = crearSemana(2026, 45);
  semana.dias[0]!.actividades[0]!.descripcion = "Actividad sintética";
  semana.dias[0]!.fotos = [
    {
      id: "foto-1",
      espacio: "A",
      archivo: new Blob(["foto"]),
      url: "blob:foto-1",
      nombre_original: "foto.jpg",
    },
  ];

  const formulario = armarFormData(semana);
  const datosCrudos = formulario.get("datos");
  if (typeof datosCrudos !== "string") throw new Error("Faltan los datos");
  const datos = JSON.parse(datosCrudos) as {
    anio: number;
    semana: number;
    dias: Array<{
      dia_semana: number;
      actividades: Array<{ letra: string }>;
      fotos: Array<{ indice: number; espacio: string }>;
      fecha?: string;
    }>;
  };

  expect(Object.keys(datos).sort()).toEqual([
    "anio",
    "dias",
    "elaborado_por_id",
    "revisado_por_id",
    "semana",
  ]);
  expect(datos.dias).toHaveLength(6);
  expect(
    datos.dias[0]!.actividades.map((actividad) => actividad.letra),
  ).toEqual(["A"]);
  expect(datos.dias[0]!.fotos).toEqual([{ indice: 0, espacio: "A" }]);
  expect(datos.dias[0]!.fecha).toBeUndefined();
  expect(formulario.getAll("fotos")).toHaveLength(1);
});

it("reconstruye dos fotos importadas en días y espacios distintos", () => {
  const contenido = btoa("foto");
  const importacion: ImportacionRead = {
    datos: {
      anio: 2026,
      semana: 45,
      elaborado_por_id: null,
      revisado_por_id: null,
      dias: Array.from({ length: 6 }, (_valor, dia_semana) => ({
        dia_semana,
        observacion: "",
        texto_fotos: "Evidencia",
        actividades: [],
        herramientas: [],
        materiales: [],
        fotos: [],
      })),
    },
    fotos: [
      { indice: 0, espacio: "A", dia_semana: 0, contenido_base64: contenido },
      { indice: 1, espacio: "AD", dia_semana: 2, contenido_base64: contenido },
    ],
    avisos: [],
    origen: "respaldo",
  };
  const crearUrl = vi
    .spyOn(URL, "createObjectURL")
    .mockReturnValueOnce("blob:foto-lunes")
    .mockReturnValueOnce("blob:foto-miercoles");

  const semana = semanaDesdeImportacion(importacion);

  expect(semana.dias[0]!.fotos[0]).toMatchObject({
    espacio: "A",
    url: "blob:foto-lunes",
  });
  expect(semana.dias[2]!.fotos[0]).toMatchObject({
    espacio: "AD",
    url: "blob:foto-miercoles",
  });
  expect(crearUrl).toHaveBeenCalledTimes(2);
});
