import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, it, vi } from "vitest";

import { Catalogos } from "./Catalogos";

const item = {
  id: 1,
  nombre: "Elemento sintético",
  orden: 1,
  activo: true,
  unidad: null,
  tipo: null,
};
const respuesta = (datos: unknown, status = 200) =>
  new Response(JSON.stringify(datos), {
    status,
    headers: { "Content-Type": "application/json" },
  });

function pagina() {
  const cliente = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={cliente}>
      <Catalogos />
    </QueryClientProvider>,
  );
}

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

it("muestra el catálogo activo", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(respuesta([item])));
  pagina();
  expect(await screen.findByText("Elemento sintético")).toBeInTheDocument();
});

it("agrega un elemento y actualiza la tabla", async () => {
  const fetchMock = vi
    .fn()
    .mockResolvedValueOnce(respuesta([]))
    .mockResolvedValueOnce(respuesta(item, 201))
    .mockResolvedValueOnce(respuesta([item]));
  vi.stubGlobal("fetch", fetchMock);
  const usuario = userEvent.setup();
  pagina();
  await screen.findByRole("table");
  await usuario.type(screen.getByLabelText("Nombre"), "Elemento sintético");
  await usuario.click(screen.getByRole("button", { name: "Agregar" }));
  await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(3));
  expect(await screen.findByText("Elemento sintético")).toBeInTheDocument();
});

it("presenta el error de la API", async () => {
  vi.stubGlobal(
    "fetch",
    vi
      .fn()
      .mockResolvedValue(
        respuesta({ detail: "Fallo sintético", code: "error" }, 500),
      ),
  );
  pagina();
  expect(await screen.findByRole("alert")).toHaveTextContent("Fallo sintético");
});
