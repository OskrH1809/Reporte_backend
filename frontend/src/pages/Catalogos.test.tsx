import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  cleanup,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, it, vi } from "vitest";

import { AvisosProvider } from "../components/Avisos";
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
  new Response(status === 204 ? null : JSON.stringify(datos), {
    status,
    headers: { "Content-Type": "application/json" },
  });

type Manejador = (url: string, init?: RequestInit) => Response | undefined;

function simularApi(colaboradores: () => unknown[], otro?: Manejador) {
  const fetchMock = vi.fn((url: string, init?: RequestInit) => {
    const extra = otro?.(url, init);
    if (extra) return Promise.resolve(extra);
    if (url === "/api/catalogos/colaboradores")
      return Promise.resolve(respuesta(colaboradores()));
    return Promise.resolve(respuesta([]));
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

function pagina() {
  const cliente = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={cliente}>
      <AvisosProvider>
        <Catalogos />
      </AvisosProvider>
    </QueryClientProvider>,
  );
}

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

it("muestra el catálogo activo con su contador", async () => {
  simularApi(() => [item]);
  pagina();
  expect(await screen.findByText("Elemento sintético")).toBeInTheDocument();
  expect(screen.getByRole("tab", { name: /Colaboradores/ })).toHaveTextContent(
    "1",
  );
});

it("agrega un elemento, avisa y actualiza la tabla", async () => {
  let lista: unknown[] = [];
  const fetchMock = simularApi(
    () => lista,
    (_url, init) => {
      if (init?.method !== "POST") return undefined;
      lista = [item];
      return respuesta(item, 201);
    },
  );
  const usuario = userEvent.setup();
  pagina();
  await screen.findByText(/No hay colaboradores/);
  await usuario.type(screen.getByLabelText("Nombre"), "Elemento sintético");
  await usuario.click(screen.getByRole("button", { name: "Agregar" }));
  expect(await screen.findByRole("status")).toHaveTextContent(
    "Se agregó «Elemento sintético».",
  );
  expect(
    await screen.findByRole("cell", { name: "Elemento sintético" }),
  ).toBeInTheDocument();
  const post = fetchMock.mock.calls.find(([, init]) => init?.method === "POST");
  expect(JSON.parse(post?.[1]?.body as string)).toEqual({
    nombre: "Elemento sintético",
  });
});

it("impide agregar un nombre repetido sin importar acentos ni mayúsculas", async () => {
  simularApi(() => [item]);
  const usuario = userEvent.setup();
  pagina();
  await screen.findByText("Elemento sintético");
  await usuario.type(screen.getByLabelText("Nombre"), "  elemento SINTETICO ");
  expect(screen.getByRole("alert")).toHaveTextContent("ya está en el catálogo");
  expect(screen.getByRole("button", { name: "Agregar" })).toBeDisabled();
});

it("pide confirmación antes de desactivar", async () => {
  let lista: unknown[] = [item];
  const fetchMock = simularApi(
    () => lista,
    (_url, init) => {
      if (init?.method !== "DELETE") return undefined;
      lista = [];
      return respuesta(null, 204);
    },
  );
  const usuario = userEvent.setup();
  pagina();
  await usuario.click(
    await screen.findByRole("button", {
      name: "Desactivar Elemento sintético",
    }),
  );
  const dialogo = screen.getByRole("dialog");
  expect(
    fetchMock.mock.calls.some(([, init]) => init?.method === "DELETE"),
  ).toBe(false);
  await usuario.click(
    within(dialogo).getByRole("button", { name: "Desactivar" }),
  );
  await waitFor(() =>
    expect(screen.queryByText("Elemento sintético")).not.toBeInTheDocument(),
  );
  expect(screen.getByRole("status")).toHaveTextContent("Se desactivó");
});

it("presenta el error de la API", async () => {
  vi.stubGlobal(
    "fetch",
    vi
      .fn()
      .mockImplementation(() =>
        Promise.resolve(
          respuesta({ detail: "Fallo sintético", code: "error" }, 500),
        ),
      ),
  );
  pagina();
  expect(await screen.findByRole("alert")).toHaveTextContent("Fallo sintético");
});
