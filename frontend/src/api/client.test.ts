import { afterEach, expect, it, vi } from "vitest";

import { apiDescarga, ApiError } from "./client";

afterEach(() => vi.unstubAllGlobals());

it("extrae el nombre de la descarga", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(
      new Response(new Blob(["archivo"]), {
        headers: {
          "Content-Disposition": 'attachment; filename="CH-RSG-45-2026.xlsx"',
        },
      }),
    ),
  );

  const resultado = await apiDescarga("/exportar/formato", new FormData());

  expect(resultado.nombre).toBe("CH-RSG-45-2026.xlsx");
});

it("propaga el detalle de un error de descarga", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          detail: "La exportación es demasiado grande",
          code: "file_too_large",
        }),
        { status: 413, headers: { "Content-Type": "application/json" } },
      ),
    ),
  );

  await expect(apiDescarga("/exportar/pdf", new FormData())).rejects.toEqual(
    new ApiError("La exportación es demasiado grande", 413, "file_too_large"),
  );
});
