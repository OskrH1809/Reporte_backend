import { afterEach, describe, expect, it, vi } from "vitest";

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

describe("sesión", () => {
  afterEach(() => {
    sessionStorage.clear();
    vi.unstubAllEnvs();
    vi.resetModules();
  });

  it("envía el token vigente y no el vencido", async () => {
    const fetchMock = vi
      .fn()
      .mockImplementation(() => Promise.resolve(new Response("{}")));
    vi.stubGlobal("fetch", fetchMock);
    const { apiRequest } = await import("./client");
    const { guardarToken } = await import("./sesion");

    await apiRequest("/catalogos/colaboradores");
    guardarToken("vigente", new Date(Date.now() + 60_000).toISOString());
    await apiRequest("/catalogos/colaboradores");
    guardarToken("vencido", new Date(Date.now() - 60_000).toISOString());
    await apiRequest("/catalogos/colaboradores");

    const cabeceras = fetchMock.mock.calls.map(
      ([, init]) => (init as RequestInit).headers as Headers,
    );
    expect(cabeceras[0]?.get("Authorization")).toBeNull();
    expect(cabeceras[1]?.get("Authorization")).toBe("Bearer vigente");
    expect(cabeceras[2]?.get("Authorization")).toBeNull();
  });

  it("usa VITE_API_URL como prefijo", async () => {
    vi.stubEnv("VITE_API_URL", "https://api.ejemplo.app/");
    const fetchMock = vi.fn().mockResolvedValue(new Response("{}"));
    vi.stubGlobal("fetch", fetchMock);
    const { apiRequest } = await import("./client");

    await apiRequest("/config");

    expect(fetchMock.mock.calls[0]?.[0]).toBe(
      "https://api.ejemplo.app/api/config",
    );
  });

  it("un 401 cierra la sesión y avisa", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            detail: "Sesión inválida",
            code: "no_autenticado",
          }),
          { status: 401 },
        ),
      ),
    );
    const { apiRequest } = await import("./client");
    const { alCerrarSesion, guardarToken, obtenerToken } =
      await import("./sesion");
    guardarToken("vigente", new Date(Date.now() + 60_000).toISOString());
    const oyente = vi.fn();
    alCerrarSesion(oyente);

    await expect(apiRequest("/catalogos/colaboradores")).rejects.toMatchObject({
      status: 401,
    });

    expect(obtenerToken()).toBeUndefined();
    expect(oyente).toHaveBeenCalledOnce();
  });
});
