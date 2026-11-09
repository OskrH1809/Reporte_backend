import { act, cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AvisosProvider, Confirmar, useAvisos } from "./Avisos";

function Disparador() {
  const { avisar } = useAvisos();
  return (
    <>
      <button type="button" onClick={() => avisar("Guardado.")}>
        ok
      </button>
      <button type="button" onClick={() => avisar("Falló.", "error")}>
        error
      </button>
    </>
  );
}

afterEach(() => {
  cleanup();
  vi.useRealTimers();
  vi.restoreAllMocks();
});

describe("avisos", () => {
  it("muestra un aviso y lo oculta solo", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(
      <AvisosProvider>
        <Disparador />
      </AvisosProvider>,
    );
    await user.click(screen.getByRole("button", { name: "ok" }));
    expect(screen.getByRole("status")).toHaveTextContent("Guardado.");
    act(() => {
      vi.advanceTimersByTime(4100);
    });
    expect(screen.queryByText("Guardado.")).not.toBeInTheDocument();
  });

  it("los errores usan role alert y se pueden cerrar", async () => {
    const user = userEvent.setup();
    render(
      <AvisosProvider>
        <Disparador />
      </AvisosProvider>,
    );
    await user.click(screen.getByRole("button", { name: "error" }));
    expect(screen.getByRole("alert")).toHaveTextContent("Falló.");
    await user.click(screen.getByRole("button", { name: "Cerrar aviso" }));
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("useAvisos falla sin proveedor", () => {
    vi.spyOn(console, "error").mockImplementation(() => undefined);
    expect(() => render(<Disparador />)).toThrow("AvisosProvider");
  });
});

describe("Confirmar", () => {
  it("no se muestra cerrado", () => {
    render(
      <Confirmar
        abierto={false}
        titulo="¿Eliminar?"
        mensaje="No se puede deshacer."
        onConfirmar={vi.fn()}
        onCancelar={vi.fn()}
      />,
    );
    expect(screen.queryByText("¿Eliminar?")).not.toBeInTheDocument();
  });

  it("llama a confirmar y cancelar", async () => {
    const user = userEvent.setup();
    const onConfirmar = vi.fn();
    const onCancelar = vi.fn();
    render(
      <Confirmar
        abierto
        titulo="¿Eliminar?"
        mensaje="No se puede deshacer."
        textoConfirmar="Eliminar"
        peligro
        onConfirmar={onConfirmar}
        onCancelar={onCancelar}
      />,
    );
    expect(screen.getByRole("button", { name: "Cancelar" })).toHaveFocus();
    await user.click(screen.getByRole("button", { name: "Eliminar" }));
    await user.click(screen.getByRole("button", { name: "Cancelar" }));
    expect(onConfirmar).toHaveBeenCalledOnce();
    expect(onCancelar).toHaveBeenCalledOnce();
  });
});
