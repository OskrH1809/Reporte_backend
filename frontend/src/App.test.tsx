import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { afterEach, expect, it, vi } from "vitest";

import { RutasAplicacion } from "./App";
import { AvisosProvider } from "./components/Avisos";

const respuesta = (datos: unknown) =>
  new Response(JSON.stringify(datos), {
    headers: { "Content-Type": "application/json" },
  });

function pagina() {
  const cliente = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={cliente}>
      <AvisosProvider>
        <MemoryRouter>
          <RutasAplicacion />
        </MemoryRouter>
      </AvisosProvider>
    </QueryClientProvider>,
  );
}

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

it("muestra la lista cuando almacenar está activo", async () => {
  const fetchMock = vi
    .fn()
    .mockResolvedValueOnce(
      respuesta({ almacenar: true, max_fotos_por_espacio: 4 }),
    )
    .mockResolvedValueOnce(respuesta([]));
  vi.stubGlobal("fetch", fetchMock);

  pagina();

  expect(
    await screen.findByRole("heading", { name: "Reportes semanales" }),
  ).toBeInTheDocument();
  expect(screen.getByRole("link", { name: /Reportes/ })).toBeInTheDocument();
});

it("muestra el editor cuando almacenar está desactivado", async () => {
  const fetchMock = vi
    .fn()
    .mockResolvedValueOnce(
      respuesta({ almacenar: false, max_fotos_por_espacio: 4 }),
    )
    .mockResolvedValue(respuesta([]));
  vi.stubGlobal("fetch", fetchMock);

  pagina();

  expect(
    await screen.findByRole("heading", { name: "Nuevo reporte semanal" }),
  ).toBeInTheDocument();
  expect(
    screen.getByRole("link", { name: /Nuevo reporte/ }),
  ).toBeInTheDocument();
});
