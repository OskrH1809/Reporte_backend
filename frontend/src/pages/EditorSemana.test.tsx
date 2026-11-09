import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { listarCatalogo } from "../api/catalogos";
import { ApiError } from "../api/client";
import { importarExcel, type ImportacionRead } from "../api/importar";
import { AvisosProvider } from "../components/Avisos";
import { EditorSemana } from "./EditorSemana";

vi.mock("../api/catalogos", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../api/catalogos")>()),
  listarCatalogo: vi.fn(),
}));
vi.mock("../api/importar", () => ({ importarExcel: vi.fn() }));

function importacion(
  avisos: string[] = [],
  origen: "respaldo" | "formato" = "respaldo",
) {
  return {
    datos: {
      anio: 2026,
      semana: 45,
      elaborado_por_id: null,
      revisado_por_id: null,
      dias: Array.from({ length: 6 }, (_valor, dia_semana) => ({
        dia_semana,
        observacion: dia_semana === 0 ? "Observación importada" : "",
        texto_fotos: "Evidencia importada",
        actividades: [],
        herramientas: [],
        materiales: [],
        fotos: [],
      })),
    },
    fotos: [],
    avisos,
    origen,
  } satisfies ImportacionRead;
}

function pagina(maxFotosPorEspacio = 4) {
  const cliente = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={cliente}>
      <AvisosProvider>
        <EditorSemana maxFotosPorEspacio={maxFotosPorEspacio} />
      </AvisosProvider>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.mocked(listarCatalogo).mockResolvedValue([]);
  vi.mocked(importarExcel).mockResolvedValue(importacion());
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

it("usa el máximo de fotos recibido desde la configuración", async () => {
  const usuario = userEvent.setup();
  pagina(2);
  const archivos = Array.from(
    { length: 3 },
    (_valor, indice) =>
      new File([`foto-${indice}`], `foto-${indice}.png`, {
        type: "image/png",
      }),
  );

  await usuario.upload(
    await screen.findByLabelText("Fotos Actividad A"),
    archivos,
  );

  expect(await screen.findByText(/el máximo es 2/)).toBeInTheDocument();
  await waitFor(() =>
    expect(screen.getAllByRole("img", { name: /foto-/ })).toHaveLength(2),
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

it("pide confirmación antes de reemplazar una semana con datos", async () => {
  const usuario = userEvent.setup();
  pagina();
  await usuario.type(
    await screen.findByLabelText("Observación"),
    "Dato actual",
  );

  await usuario.upload(
    screen.getByLabelText("Archivo de reporte guardado"),
    new File(["excel"], "reporte.xlsx"),
  );

  expect(importarExcel).not.toHaveBeenCalled();
  expect(
    screen.getByText(/Se reemplazará la semana actual/),
  ).toBeInTheDocument();
  await usuario.click(screen.getByRole("button", { name: "Abrir reporte" }));
  await waitFor(() => expect(importarExcel).toHaveBeenCalledOnce());
});

it("muestra avisos y la advertencia del formato sin respaldo", async () => {
  const usuario = userEvent.setup();
  vi.mocked(importarExcel).mockResolvedValue(
    importacion(["Aviso sintético"], "formato"),
  );
  pagina();

  await usuario.upload(
    screen.getByLabelText("Archivo de reporte guardado"),
    new File(["excel"], "reporte.xlsx"),
  );

  expect(await screen.findByText("Revisa estos puntos")).toBeInTheDocument();
  expect(screen.getByText("Aviso sintético")).toBeInTheDocument();
  expect(
    screen.getByText(/Se leyó el formato sin respaldo/),
  ).toBeInTheDocument();
});

it("muestra el detalle de un error 422", async () => {
  const usuario = userEvent.setup();
  vi.mocked(importarExcel).mockRejectedValue(
    new ApiError("El respaldo está dañado", 422, "invalid_file"),
  );
  pagina();

  await usuario.upload(
    screen.getByLabelText("Archivo de reporte guardado"),
    new File(["excel"], "reporte.xlsx"),
  );

  expect(await screen.findByRole("alert")).toHaveTextContent(
    "El respaldo está dañado",
  );
});
