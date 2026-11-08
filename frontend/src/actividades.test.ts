import { expect, it } from "vitest";

import type { Actividad, Foto, Letra } from "./api/reportes";
import {
  armarActividades,
  espaciosFotos,
  puedeQuitar,
  siguienteLetra,
} from "./actividades";

const actividad = (
  letra: Letra,
  cambios: Partial<Actividad> = {},
): Actividad => ({
  letra,
  descripcion: "",
  asignaciones: [],
  ...cambios,
});

const foto = (espacio: Foto["espacio"]): Foto => ({
  id: 1,
  espacio,
  orden: 1,
  nombre_original: "sintetica.jpg",
  url: "/fotos/1",
});

it("arma A y B para un día vacío", () => {
  expect(armarActividades([]).map((item) => item.letra)).toEqual(["A", "B"]);
});

it("rellena los huecos hasta la letra más alta guardada", () => {
  const resultado = armarActividades([
    actividad("A", { descripcion: "Primera" }),
    actividad("D", { descripcion: "Cuarta" }),
  ]);

  expect(resultado.map((item) => item.letra)).toEqual(["A", "B", "C", "D"]);
  expect(resultado.slice(1, 3).map((item) => item.descripcion)).toEqual([
    "",
    "",
  ]);
});

it("no ofrece una letra después de J", () => {
  const actividades = "ABCDEFGHIJ"
    .split("")
    .map((letra) => actividad(letra as Letra));
  expect(siguienteLetra(actividades)).toBeUndefined();
});

it("solo permite quitar la última actividad vacía posterior a B y sin fotos", () => {
  const vacia = actividad("C");
  const conPersona = actividad("C", {
    asignaciones: [{ colaborador_id: 1, horas_manual: false }],
  });

  expect(puedeQuitar(actividad("B"), true, [])).toBe(false);
  expect(
    puedeQuitar(actividad("C", { descripcion: "Capturada" }), true, []),
  ).toBe(false);
  expect(puedeQuitar(conPersona, true, [])).toBe(false);
  expect(puedeQuitar(vacia, true, [foto("C")])).toBe(false);
  expect(puedeQuitar(vacia, false, [])).toBe(false);
  expect(puedeQuitar(vacia, true, [])).toBe(true);
});

it("crea espacios de cuatro fotos para actividades visibles y antes y después", () => {
  const espacios = espaciosFotos([
    actividad("A"),
    actividad("B"),
    actividad("C"),
  ]);

  expect(espacios).toHaveLength(4);
  expect(espacios.map(([espacio]) => espacio)).toEqual(["A", "B", "C", "AD"]);
  expect(espacios.every(([, , maximo]) => maximo === 4)).toBe(true);
});
