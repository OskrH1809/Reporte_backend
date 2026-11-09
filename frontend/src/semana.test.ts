import { expect, it } from "vitest";

import { armarFormData, crearSemana } from "./semana";

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
