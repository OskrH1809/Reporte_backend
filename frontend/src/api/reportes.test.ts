import { expect, it } from "vitest";

import { type DiaInput, serializarDia } from "./reportes";

it("envía solo los campos editables del día", () => {
  const dia = {
    id: 9,
    fotos: [],
    observacion: "Nota",
    texto_fotos: "Fotos",
    herramientas: [{ herramienta_id: 1, nombre: "Pala", cantidad: 2 }],
    materiales: [
      { material_id: 3, nombre: "Cloro", unidad: "litro", cantidad: 1 },
    ],
    actividades: [
      {
        id: 7,
        letra: "A",
        descripcion: "Aseo",
        personas: 1,
        horas_hombre: 8,
        asignaciones: [
          {
            id: 5,
            colaborador_id: 2,
            colaborador_nombre: "Persona Prueba",
            horas: 8,
            horas_manual: false,
          },
        ],
      },
    ],
  } as unknown as DiaInput;

  expect(serializarDia(dia)).toEqual({
    observacion: "Nota",
    texto_fotos: "Fotos",
    herramientas: [{ herramienta_id: 1, cantidad: 2 }],
    materiales: [{ material_id: 3, cantidad: 1 }],
    actividades: [
      {
        letra: "A",
        descripcion: "Aseo",
        asignaciones: [{ colaborador_id: 2, horas: 8, horas_manual: false }],
      },
    ],
  });
});
