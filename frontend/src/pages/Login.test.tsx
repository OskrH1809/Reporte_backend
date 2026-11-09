import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, it, vi } from "vitest";

import { obtenerToken } from "../api/sesion";
import { Login } from "./Login";

const respuesta = (datos: unknown, status = 200) =>
  new Response(JSON.stringify(datos), {
    status,
    headers: { "Content-Type": "application/json" },
  });

function pagina(onEntrar = vi.fn()) {
  const cliente = new QueryClient({
    defaultOptions: { mutations: { retry: false } },
  });
  render(
    <QueryClientProvider client={cliente}>
      <Login onEntrar={onEntrar} />
    </QueryClientProvider>,
  );
  return onEntrar;
}

async function entrar() {
  const usuario = userEvent.setup();
  await usuario.type(screen.getByLabelText("Correo"), "admin@ejemplo.com");
  await usuario.type(screen.getByLabelText("Contraseña"), "contrasena-larga");
  await usuario.click(screen.getByRole("button", { name: "Entrar" }));
}

afterEach(() => {
  cleanup();
  sessionStorage.clear();
  vi.unstubAllGlobals();
});

it("guarda el token y avisa al entrar", async () => {
  const expira = new Date(Date.now() + 3_600_000).toISOString();
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(
      respuesta({
        access_token: "token",
        token_type: "bearer",
        expira_en: expira,
      }),
    ),
  );
  const onEntrar = pagina();

  await entrar();

  await vi.waitFor(() => expect(onEntrar).toHaveBeenCalledOnce());
  expect(obtenerToken()).toBe("token");
});

it.each([
  [401, "credenciales_invalidas", "Correo o contraseña incorrectos."],
  [429, "demasiados_intentos", "Demasiados intentos. Espera 15 minutos."],
])("muestra el mensaje de %s", async (status, code, mensaje) => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(respuesta({ detail: "x", code }, status)),
  );
  const onEntrar = pagina();

  await entrar();

  expect(await screen.findByRole("alert")).toHaveTextContent(mensaje);
  expect(onEntrar).not.toHaveBeenCalled();
});

it("avisa si no hay conexión", async () => {
  vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("red")));
  pagina();

  await entrar();

  expect(await screen.findByRole("alert")).toHaveTextContent(
    "No se pudo conectar con el servidor.",
  );
});
