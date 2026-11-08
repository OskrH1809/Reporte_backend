import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { type Catalogo, listarCatalogo } from "../api/catalogos";
import {
  LETRAS,
  editarReporte,
  eliminarFoto,
  guardarDia,
  subirFotos,
  verDia,
  verReporte,
} from "../api/reportes";
import { EditorReporte } from "../pages/EditorReporte";
import { AvisosProvider } from "./Avisos";
import { SelectorColaboradores } from "./SelectorColaboradores";
import { SelectorFotos } from "./SelectorFotos";
import { TablaCantidades } from "./TablaCantidades";

vi.mock("../api/catalogos", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../api/catalogos")>()),
  listarCatalogo: vi.fn(),
}));
vi.mock("../api/reportes", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../api/reportes")>()),
  editarReporte: vi.fn(),
  eliminarFoto: vi.fn(),
  guardarDia: vi.fn(),
  subirFotos: vi.fn(),
  verDia: vi.fn(),
  verReporte: vi.fn(),
}));

const catalogo: Catalogo = {
  id: 1,
  nombre: "Elemento sintético",
  orden: 1,
  activo: true,
  unidad: "unidad",
  tipo: null,
};

afterEach(cleanup);

const dia = {
  id: 1,
  dia_semana: 0,
  fecha: "2026-09-14",
  observacion: "",
  texto_fotos: "",
  actividades: [],
  herramientas: [],
  materiales: [],
  fotos: [],
  personas: 0,
  horas_hombre: 0,
  numero_actividades: 0,
  advertencias: [],
};

function paginaEditor() {
  const cliente = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={cliente}>
      <AvisosProvider>
        <MemoryRouter initialEntries={["/reportes/1"]}>
          <Routes>
            <Route path="/reportes/:id" element={<EditorReporte />} />
          </Routes>
        </MemoryRouter>
      </AvisosProvider>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(listarCatalogo).mockResolvedValue([]);
  vi.mocked(verReporte).mockResolvedValue({
    id: 1,
    anio: 2026,
    semana: 38,
    codigo: "CH-RSG-38-2026",
    fecha_inicio: "2026-09-14",
    fecha_fin: "2026-09-19",
    elaborado_por_id: null,
    revisado_por_id: null,
    horas_hombre: 0,
  });
  vi.mocked(verDia).mockResolvedValue(dia);
  vi.mocked(guardarDia).mockResolvedValue(dia);
  vi.mocked(editarReporte).mockResolvedValue({
    id: 1,
    anio: 2026,
    semana: 38,
    codigo: "CH-RSG-38-2026",
    fecha_inicio: "2026-09-14",
    fecha_fin: "2026-09-19",
    elaborado_por_id: null,
    revisado_por_id: null,
    horas_hombre: 0,
  });
  vi.mocked(subirFotos).mockResolvedValue();
  vi.mocked(eliminarFoto).mockResolvedValue();
});

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
  expect(onChange).toHaveBeenCalledWith([
    {
      material_id: 1,
      cantidad: 1,
      nombre: "Elemento sintético",
      unidad: "unidad",
    },
  ]);
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
      subiendo={false}
      onSubir={vi.fn()}
      onEliminar={vi.fn()}
    />,
  );
  expect(screen.getByText("2/2")).toBeInTheDocument();
  expect(screen.getByLabelText("Fotos Actividad A")).toBeDisabled();
});

it("conserva el borrador después de subir una foto", async () => {
  const usuario = userEvent.setup();
  paginaEditor();
  const capturar = (
    await screen.findAllByRole("button", { name: "Capturar" })
  )[0]!;
  await usuario.click(capturar);
  const descripcion = screen.getByLabelText("Descripción");
  await usuario.type(descripcion, "Descripción sintética");
  await usuario.upload(
    screen.getByLabelText("Fotos Actividad A"),
    new File(["imagen sintética"], "sintetica.png", { type: "image/png" }),
  );
  await waitFor(() => expect(subirFotos).toHaveBeenCalledOnce());
  await usuario.click(screen.getByRole("button", { name: "Guardar" }));
  expect(guardarDia).toHaveBeenCalledWith(
    1,
    0,
    expect.objectContaining({
      actividades: [
        expect.objectContaining({ descripcion: "Descripción sintética" }),
      ],
    }),
  );
});

it("muestra el error al subir una foto", async () => {
  vi.mocked(subirFotos).mockRejectedValue(new Error("Fallo sintético"));
  const usuario = userEvent.setup();
  paginaEditor();
  await screen.findAllByRole("button", { name: "Capturar" });
  await usuario.upload(
    screen.getByLabelText("Fotos Actividad A"),
    new File(["imagen sintética"], "sintetica.png", { type: "image/png" }),
  );
  expect(await screen.findByRole("alert")).toHaveTextContent("Fallo sintético");
});

it("deshabilita Guardar cuando una verificación tiene error", async () => {
  vi.mocked(listarCatalogo).mockImplementation((tipo) =>
    Promise.resolve(tipo === "colaboradores" ? [catalogo] : []),
  );
  vi.mocked(verDia).mockResolvedValue({
    ...dia,
    actividades: [
      {
        letra: "A",
        descripcion: "Actividad sintética",
        asignaciones: [
          {
            colaborador_id: 1,
            horas: 9,
            horas_manual: true,
          },
        ],
      },
    ],
  });
  paginaEditor();
  const guardarBoton = await screen.findByRole("button", { name: "Guardar" });
  expect(guardarBoton).toBeDisabled();
  await waitFor(() =>
    expect(guardarBoton).toHaveAttribute(
      "title",
      "Corrige los errores de verificación antes de guardar.",
    ),
  );
});

it("despliega una actividad vacía al pulsar Capturar", async () => {
  const usuario = userEvent.setup();
  paginaEditor();
  const botones = await screen.findAllByRole("button", { name: "Capturar" });
  expect(screen.queryByLabelText("Descripción")).not.toBeInTheDocument();
  await usuario.click(botones[0]!);
  expect(screen.getByLabelText("Descripción")).toBeInTheDocument();
});

it("muestra un aviso al guardar el día", async () => {
  const usuario = userEvent.setup();
  paginaEditor();
  await usuario.type(
    await screen.findByLabelText("Observación"),
    "Feriado sintético",
  );
  await usuario.click(screen.getByRole("button", { name: "Guardar" }));
  expect(await screen.findByText("Día guardado.")).toBeInTheDocument();
});

it("muestra solo actividades A y B para un día vacío", async () => {
  paginaEditor();

  await screen.findByText(/Actividad A ·/);
  expect(screen.getByText(/Actividad B ·/)).toBeInTheDocument();
  expect(screen.queryByText(/Actividad C ·/)).not.toBeInTheDocument();
});

it("agrega la siguiente actividad y su espacio de fotos", async () => {
  const usuario = userEvent.setup();
  paginaEditor();
  await screen.findByText(/Actividad A ·/);

  await usuario.click(
    screen.getByRole("button", { name: "Agregar actividad" }),
  );

  expect(
    screen.getByRole("heading", { name: "Actividad C", level: 2 }),
  ).toBeInTheDocument();
  expect(screen.getByLabelText("Fotos Actividad C")).toBeInTheDocument();
});

it("deshabilita agregar al llegar a J", async () => {
  vi.mocked(verDia).mockResolvedValue({
    ...dia,
    actividades: LETRAS.map((letra) => ({
      letra,
      descripcion: `Descripción ${letra}`,
      asignaciones: [],
    })),
  });
  paginaEditor();

  const boton = await screen.findByRole("button", {
    name: "Agregar actividad",
  });
  await waitFor(() => expect(boton).toBeDisabled());
  expect(boton).toHaveAttribute("title", "Máximo 10 actividades por día");
});

it("no permite quitar B y quita C cuando está vacía", async () => {
  const usuario = userEvent.setup();
  paginaEditor();
  await screen.findByText(/Actividad B ·/);
  expect(
    screen.queryByRole("button", { name: "Quitar" }),
  ).not.toBeInTheDocument();

  await usuario.click(
    screen.getByRole("button", { name: "Agregar actividad" }),
  );
  await usuario.click(screen.getByRole("button", { name: "Quitar" }));

  expect(
    screen.queryByRole("heading", { name: "Actividad C", level: 2 }),
  ).not.toBeInTheDocument();
  expect(screen.queryByLabelText("Fotos Actividad C")).not.toBeInTheDocument();
});
