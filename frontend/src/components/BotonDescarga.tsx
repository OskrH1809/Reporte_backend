import { useState } from "react";

import { apiDescarga } from "../api/client";
import { useAvisos } from "./Avisos";

interface Props {
  tipo: "formato" | "mejorado" | "pdf";
  etiqueta: string;
  obtenerDatos: () => FormData;
  deshabilitado?: boolean;
}

export function BotonDescarga({
  tipo,
  etiqueta,
  obtenerDatos,
  deshabilitado = false,
}: Props) {
  const [generando, setGenerando] = useState(false);
  const { avisar } = useAvisos();

  async function descargar() {
    setGenerando(true);
    try {
      const resultado = await apiDescarga(`/exportar/${tipo}`, obtenerDatos());
      const url = URL.createObjectURL(resultado.blob);
      const enlace = document.createElement("a");
      enlace.href = url;
      enlace.download =
        resultado.nombre ?? `reporte.${tipo === "pdf" ? "pdf" : "xlsx"}`;
      document.body.append(enlace);
      enlace.click();
      enlace.remove();
      URL.revokeObjectURL(url);
    } catch (error) {
      avisar(
        error instanceof Error
          ? error.message
          : "No se pudo generar el archivo.",
        "error",
      );
    } finally {
      setGenerando(false);
    }
  }

  return (
    <button
      type="button"
      className="btn-secondary btn-sm"
      disabled={deshabilitado || generando}
      onClick={() => void descargar()}
    >
      {generando ? "Generando…" : etiqueta}
    </button>
  );
}
