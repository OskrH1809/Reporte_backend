import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { listarCatalogo } from "../api/catalogos";
import { AvisosProvider } from "../components/Avisos";
import { EditorSemana } from "./EditorSemana";

vi.mock("../api/catalogos", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../api/catalogos")>()),
  listarCatalogo: vi.fn(),
}));

function pagina() {
  const cliente = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={cliente}>
      <AvisosProvider>
        <EditorSemana />
      </AvisosProvider>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.mocked(listarCatalogo).mockResolvedValue([]);
  vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:foto-sintetica");
  vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => undefined);
  vi.stubGlobal(
    "createImageBitmap",
    vi.fn().mockRejectedValue(new Error("sin canvas")),
  );
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

it("conserva el lunes al cambiar de día y volver", async () => {
  const usuario = userEvent.setup();
  pagina();
  await usuario.click(
    (await screen.findAllByRole("button", { name: "Capturar" }))[0]!,
  );
  await usuario.type(
    screen.getByLabelText("Descripción"),
    "Actividad del lunes",
  );

  await usuario.click(screen.getByRole("tab", { name: /Martes/ }));
  await usuario.click(screen.getByRole("tab", { name: /Lunes/ }));

  expect(screen.getByLabelText("Descripción")).toHaveValue(
    "Actividad del lunes",
  );
});

it("avisa y limita la quinta foto", async () => {
  const usuario = userEvent.setup();
  pagina();
  const archivos = Array.from(
    { length: 5 },
    (_valor, indice) =>
      new File([`foto-${indice}`], `foto-${indice}.png`, { type: "image/png" }),
  );

  await usuario.upload(
    await screen.findByLabelText("Fotos Actividad A"),
    archivos,
  );

  expect(
    await screen.findByText(/Solo se agregaron 4 foto/),
  ).toBeInTheDocument();
  await waitFor(() =>
    expect(screen.getAllByRole("img", { name: /foto-/ })).toHaveLength(4),
  );
});

it("pide confirmación antes de crear otra semana con datos", async () => {
  const usuario = userEvent.setup();
  pagina();
  await usuario.type(
    await screen.findByLabelText("Observación"),
    "Dato sintético",
  );

  await usuario.click(screen.getByRole("button", { name: "Nueva semana" }));

  expect(
    screen.getByRole("heading", { name: "Nueva semana" }),
  ).toBeInTheDocument();
  expect(screen.getByText(/Hay datos sin descargar/)).toBeInTheDocument();
});
