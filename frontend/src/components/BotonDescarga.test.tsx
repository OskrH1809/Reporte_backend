import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, it, vi } from "vitest";

import { apiDescarga } from "../api/client";
import { AvisosProvider } from "./Avisos";
import { BotonDescarga } from "./BotonDescarga";

vi.mock("../api/client", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../api/client")>()),
  apiDescarga: vi.fn(),
}));

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
  vi.unstubAllGlobals();
});

function pagina() {
  return render(
    <AvisosProvider>
      <BotonDescarga
        tipo="formato"
        etiqueta="Formato actual"
        obtenerDatos={() => new FormData()}
      />
    </AvisosProvider>,
  );
}

it("descarga con el nombre enviado por el servidor", async () => {
  vi.mocked(apiDescarga).mockResolvedValue({
    blob: new Blob(["archivo"]),
    nombre: "CH-RSG-45-2026.xlsx",
  });
  const revocar = vi.fn();
  vi.stubGlobal("URL", {
    ...URL,
    createObjectURL: vi.fn(() => "blob:descarga"),
    revokeObjectURL: revocar,
  });
  let nombreDescarga = "";
  const click = vi
    .spyOn(HTMLAnchorElement.prototype, "click")
    .mockImplementation(function (this: HTMLAnchorElement) {
      nombreDescarga = this.download;
    });
  pagina();

  await userEvent.click(screen.getByRole("button", { name: "Formato actual" }));

  await waitFor(() => expect(click).toHaveBeenCalledOnce());
  expect(nombreDescarga).toBe("CH-RSG-45-2026.xlsx");
  expect(revocar).toHaveBeenCalledWith("blob:descarga");
});

it("avisa el detalle del error", async () => {
  vi.mocked(apiDescarga).mockRejectedValue(new Error("Límite sintético"));
  pagina();

  await userEvent.click(screen.getByRole("button", { name: "Formato actual" }));

  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Límite sintético",
  );
});
