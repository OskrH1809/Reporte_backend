import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, it, vi } from "vitest";

import type { Catalogo } from "../api/catalogos";
import { SelectorColaboradores } from "./SelectorColaboradores";
import { SelectorFotos } from "./SelectorFotos";
import { TablaCantidades } from "./TablaCantidades";

const catalogo: Catalogo = {
  id: 1,
  nombre: "Elemento sintético",
  orden: 1,
  activo: true,
  unidad: "unidad",
  tipo: null,
};

afterEach(cleanup);

it("selecciona un colaborador", async () => {
  const onChange = vi.fn();
  render(
    <SelectorColaboradores
      colaboradores={[catalogo]}
      valor={[]}
      onChange={onChange}
    />,
  );
  await userEvent.click(
    screen.getByRole("button", { name: "Elemento sintético" }),
  );
  expect(onChange).toHaveBeenCalledWith([
    expect.objectContaining({ colaborador_id: 1, horas_manual: false }),
  ]);
});

it("agrega un material con cantidad inicial", async () => {
  const onChange = vi.fn();
  render(
    <TablaCantidades
      titulo="Materiales"
      tipo="material"
      catalogo={[catalogo]}
      valor={[]}
      onChange={onChange}
    />,
  );
  await userEvent.selectOptions(
    screen.getByLabelText("Agregar materiales"),
    "1",
  );
  expect(onChange).toHaveBeenCalledWith([{ material_id: 1, cantidad: 1 }]);
});

it("muestra el contador y bloquea un espacio lleno", () => {
  render(
    <SelectorFotos
      espacio="A"
      etiqueta="Actividad A"
      maximo={2}
      fotos={[
        {
          id: 1,
          espacio: "A",
          orden: 1,
          nombre_original: "uno.jpg",
          url: "/api/fotos/1/archivo",
        },
        {
          id: 2,
          espacio: "A",
          orden: 2,
          nombre_original: "dos.jpg",
          url: "/api/fotos/2/archivo",
        },
      ]}
      onSubir={vi.fn()}
      onEliminar={vi.fn()}
    />,
  );
  expect(screen.getByText("2/2")).toBeInTheDocument();
  expect(screen.getByLabelText("Fotos Actividad A")).toBeDisabled();
});
