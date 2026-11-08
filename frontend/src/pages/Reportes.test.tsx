import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { afterEach, expect, it, vi } from "vitest";

import { AvisosProvider } from "../components/Avisos";
import { Reportes } from "./Reportes";

const reporte = {
  id: 7,
  anio: 2026,
  semana: 38,
  codigo: "CH-RSG-38-2026",
  fecha_inicio: "2026-09-14",
  fecha_fin: "2026-09-19",
  elaborado_por_id: null,
  revisado_por_id: null,
  horas_hombre: 104,
};
const respuesta = (datos: unknown, status = 200) =>
  new Response(status === 204 ? null : JSON.stringify(datos), {
    status,
    headers: { "Content-Type": "application/json" },
  });

function pagina() {
  const cliente = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={cliente}>
      <AvisosProvider>
        <MemoryRouter>
          <Reportes />
        </MemoryRouter>
      </AvisosProvider>
    </QueryClientProvider>,
  );
}

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

async function elegirSemana(anio: string, semana: string) {
  const usuario = userEvent.setup();
  await usuario.clear(screen.getByLabelText("Año"));
  await usuario.type(screen.getByLabelText("Año"), anio);
  await usuario.clear(screen.getByLabelText("Semana"));
  await usuario.type(screen.getByLabelText("Semana"), semana);
  return usuario;
}

it("lista los reportes con sus fechas y horas", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(respuesta([reporte])));
  pagina();
  expect(await screen.findByText("CH-RSG-38-2026")).toBeInTheDocument();
  expect(screen.getByText("14 sep – 19 sep 2026")).toBeInTheDocument();
  expect(screen.getByText("104 h")).toBeInTheDocument();
});

it("muestra las fechas de la semana elegida y valida el rango", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(respuesta([])));
  pagina();
  await screen.findByText(/Aún no hay reportes/);
  await elegirSemana("2026", "54");
  expect(screen.getByRole("alert")).toHaveTextContent(
    "La semana debe estar entre 1 y 53 para 2026.",
  );
  await elegirSemana("2025", "53");
  expect(screen.getByRole("alert")).toHaveTextContent("entre 1 y 52");
  expect(screen.getByRole("button", { name: "Crear reporte" })).toBeDisabled();
  await elegirSemana("2026", "38");
  expect(screen.getByText("14 sep – 19 sep 2026")).toBeInTheDocument();
});

it("avisa si el reporte ya existe y no deja crearlo de nuevo", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(respuesta([reporte])));
  pagina();
  await screen.findByText("CH-RSG-38-2026");
  await elegirSemana("2026", "38");
  expect(screen.getByRole("status")).toHaveTextContent(
    "Ya existe CH-RSG-38-2026.",
  );
  expect(screen.getByRole("button", { name: "Crear reporte" })).toBeDisabled();
});

it("pide confirmación antes de eliminar", async () => {
  const fetchMock = vi
    .fn()
    .mockResolvedValueOnce(respuesta([reporte]))
    .mockResolvedValueOnce(respuesta(null, 204))
    .mockResolvedValue(respuesta([]));
  vi.stubGlobal("fetch", fetchMock);
  const usuario = userEvent.setup();
  pagina();
  await usuario.click(
    await screen.findByRole("button", { name: "Eliminar CH-RSG-38-2026" }),
  );
  expect(fetchMock).toHaveBeenCalledTimes(1);
  await usuario.click(screen.getByRole("button", { name: "Eliminar" }));
  expect(await screen.findByRole("status")).toHaveTextContent(
    "Reporte CH-RSG-38-2026 eliminado.",
  );
  expect(fetchMock.mock.calls[1]).toEqual([
    "/api/reportes/7",
    expect.objectContaining({ method: "DELETE" }),
  ]);
});
