import { expect, it } from "vitest";

import type { Actividad } from "./api/reportes";
import { calcularHoras } from "./calculos";

const actividad = (letra: Actividad["letra"], manual = false): Actividad => ({
  letra,
  descripcion: `Actividad ${letra}`,
  asignaciones: [
    {
      colaborador_id: 1,
      horas: manual ? 3 : undefined,
      horas_manual: manual,
    },
  ],
});

it("asigna la jornada completa en una actividad", () => {
  expect(calcularHoras([actividad("A")], 8)[0]!.asignaciones[0]!.horas).toBe(8);
});

it("reparte la jornada entre dos actividades", () => {
  const resultado = calcularHoras([actividad("A"), actividad("B")], 8);
  expect(resultado.map((item) => item.asignaciones[0]!.horas)).toEqual([4, 4]);
});

it("conserva horas manuales y reparte el resto", () => {
  const resultado = calcularHoras([actividad("A", true), actividad("B")], 8);
  expect(resultado.map((item) => item.asignaciones[0]!.horas)).toEqual([3, 5]);
  expect(resultado[0]!.asignaciones[0]!.horas_manual).toBe(true);
});

it("usa jornada de cinco horas el sábado", () => {
  expect(calcularHoras([actividad("A")], 5)[0]!.asignaciones[0]!.horas).toBe(5);
});
