import { describe, expect, it } from "vitest";

import type { Actividad, Cantidad, Foto } from "./api/reportes";
import { verificarDia } from "./verificaciones";

const actividad = (
  letra: Actividad["letra"],
  descripcion = `Actividad ${letra}`,
  horas: number | undefined = 8,
): Actividad => ({
  letra,
  descripcion,
  asignaciones: [
    { colaborador_id: 1, horas, horas_manual: horas !== undefined },
  ],
});

const foto = (espacio: Foto["espacio"]): Foto => ({
  id: 1,
  espacio,
  orden: 1,
  nombre_original: "imagen.jpg",
  url: "/fotos/imagen.jpg",
});

const base = (actividades: Actividad[] = [actividad("A")]) => ({
  actividades,
  herramientas: [{ nombre: "Escoba", cantidad: 1 }] as Cantidad[],
  materiales: [] as Cantidad[],
  fotos: [foto("A")],
  observacion: "",
  jornada: 8,
  nombres: new Map([[1, "Ana Pérez"]]),
});

describe("verificarDia", () => {
  it("marca como error a quien supera la jornada", () => {
    const entrada = base([
      actividad("A", "Primera", 5),
      actividad("B", "Segunda", 4),
    ]);
    entrada.fotos.push(foto("B"));
    expect(verificarDia(entrada)[0]).toEqual({
      nivel: "error",
      mensaje: "Ana Pérez suma 9 h; la jornada es de 8 h.",
      seccion: "actividades",
    });
  });

  it("marca como error las horas vacías", () => {
    const sinHoras = actividad("A");
    sinHoras.asignaciones[0]!.horas = undefined;
    expect(verificarDia(base([sinHoras]))).toContainEqual({
      nivel: "error",
      mensaje: "Ana Pérez no tiene horas en la actividad A.",
      seccion: "actividades",
    });
  });

  it("marca como error una actividad con personas sin descripción", () => {
    expect(verificarDia(base([actividad("A", " ")]))).toContainEqual({
      nivel: "error",
      mensaje: "La actividad A tiene personas pero no descripción.",
      seccion: "actividades",
    });
  });

  it("marca como error cantidades no positivas o no finitas", () => {
    const entrada = base();
    entrada.herramientas = [{ nombre: "Escoba", cantidad: 0 }];
    entrada.materiales = [{ cantidad: Number.NaN }];
    expect(verificarDia(entrada)).toEqual(
      expect.arrayContaining([
        {
          nivel: "error",
          mensaje: "La cantidad de Escoba debe ser mayor que 0.",
          seccion: "herramientas",
        },
        {
          nivel: "error",
          mensaje: "La cantidad de un elemento debe ser mayor que 0.",
          seccion: "materiales",
        },
      ]),
    );
  });

  it("avisa cuando una descripción no tiene personas", () => {
    const entrada = base([
      { letra: "A", descripcion: "Limpieza", asignaciones: [] },
    ]);
    expect(verificarDia(entrada)).toContainEqual({
      nivel: "aviso",
      mensaje: "La actividad A no tiene personas asignadas.",
      seccion: "actividades",
    });
  });

  it("avisa cuando una persona no completa la jornada", () => {
    expect(verificarDia(base([actividad("A", "Limpieza", 7)]))).toContainEqual({
      nivel: "aviso",
      mensaje: "Ana Pérez suma 7 h de 8 h.",
      seccion: "actividades",
    });
  });

  it("avisa cuando una actividad con descripción no tiene fotos", () => {
    const entrada = base();
    entrada.fotos = [];
    expect(verificarDia(entrada)).toContainEqual({
      nivel: "aviso",
      mensaje: "La actividad A no tiene fotos.",
      seccion: "fotos",
    });
  });

  it("avisa cuando un día vacío tampoco tiene observación", () => {
    const entrada = base([]);
    entrada.fotos = [];
    expect(verificarDia(entrada)).toContainEqual({
      nivel: "aviso",
      mensaje:
        "Día sin actividades: escribe una observación (por ejemplo, feriado).",
      seccion: "general",
    });
  });

  it("avisa cuando hay personas pero no herramientas", () => {
    const entrada = base();
    entrada.herramientas = [];
    expect(verificarDia(entrada)).toContainEqual({
      nivel: "aviso",
      mensaje: "No se registraron herramientas.",
      seccion: "herramientas",
    });
  });

  it("no devuelve verificaciones para un día completo", () => {
    expect(verificarDia(base())).toEqual([]);
  });

  it("mantiene el orden definido de las reglas", () => {
    const entrada = base([
      actividad("A", "", 9),
      { letra: "B", descripcion: "Segunda", asignaciones: [] },
    ]);
    entrada.herramientas = [{ nombre: "Escoba", cantidad: 0 }];
    entrada.fotos = [];
    expect(verificarDia(entrada).map(({ mensaje }) => mensaje)).toEqual([
      "Ana Pérez suma 9 h; la jornada es de 8 h.",
      "La actividad A tiene personas pero no descripción.",
      "La cantidad de Escoba debe ser mayor que 0.",
      "La actividad B no tiene personas asignadas.",
      "La actividad B no tiene fotos.",
    ]);
  });
});
