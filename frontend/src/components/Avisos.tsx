import {
  createContext,
  type ReactNode,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

export type NivelAviso = "ok" | "error" | "info";

interface Aviso {
  id: number;
  mensaje: string;
  nivel: NivelAviso;
}

interface ContextoAvisos {
  avisar: (mensaje: string, nivel?: NivelAviso) => void;
}

const Contexto = createContext<ContextoAvisos | null>(null);

const DURACION: Record<NivelAviso, number> = {
  ok: 4000,
  info: 4000,
  error: 8000,
};

export function AvisosProvider({ children }: { children: ReactNode }) {
  const [avisos, setAvisos] = useState<Aviso[]>([]);
  const siguiente = useRef(0);
  const quitar = useCallback(
    (id: number) => setAvisos((lista) => lista.filter((a) => a.id !== id)),
    [],
  );
  const avisar = useCallback(
    (mensaje: string, nivel: NivelAviso = "ok") => {
      const id = ++siguiente.current;
      setAvisos((lista) => [...lista.slice(-3), { id, mensaje, nivel }]);
      window.setTimeout(() => quitar(id), DURACION[nivel]);
    },
    [quitar],
  );
  const valor = useMemo(() => ({ avisar }), [avisar]);
  return (
    <Contexto.Provider value={valor}>
      {children}
      <div className="toasts" aria-live="polite">
        {avisos.map((aviso) => (
          <div
            key={aviso.id}
            className={`toast toast-${aviso.nivel}`}
            role={aviso.nivel === "error" ? "alert" : "status"}
          >
            <p>{aviso.mensaje}</p>
            <button
              type="button"
              className="btn-ghost btn-icon btn-sm"
              aria-label="Cerrar aviso"
              onClick={() => quitar(aviso.id)}
            >
              ✕
            </button>
          </div>
        ))}
      </div>
    </Contexto.Provider>
  );
}

export function useAvisos(): ContextoAvisos {
  const contexto = useContext(Contexto);
  if (!contexto) throw new Error("useAvisos requiere AvisosProvider");
  return contexto;
}

interface ConfirmarProps {
  abierto: boolean;
  titulo: string;
  mensaje: string;
  textoConfirmar?: string;
  peligro?: boolean;
  onConfirmar: () => void;
  onCancelar: () => void;
}

export function Confirmar({
  abierto,
  titulo,
  mensaje,
  textoConfirmar = "Confirmar",
  peligro = false,
  onConfirmar,
  onCancelar,
}: ConfirmarProps) {
  const dialogo = useRef<HTMLDialogElement>(null);
  const cancelar = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    const nodo = dialogo.current;
    if (!nodo || !abierto) return;
    if (typeof nodo.showModal === "function" && !nodo.open) nodo.showModal();
    cancelar.current?.focus();
    return () => {
      if (typeof nodo.close === "function" && nodo.open) nodo.close();
    };
  }, [abierto]);
  if (!abierto) return null;
  return (
    <dialog
      ref={dialogo}
      className="dialogo"
      aria-labelledby="confirmar-titulo"
      open={typeof HTMLDialogElement.prototype.showModal !== "function"}
      onCancel={(event) => {
        event.preventDefault();
        onCancelar();
      }}
    >
      <h2 id="confirmar-titulo">{titulo}</h2>
      <p>{mensaje}</p>
      <div className="cluster">
        <button
          ref={cancelar}
          type="button"
          className="btn-secondary"
          onClick={onCancelar}
        >
          Cancelar
        </button>
        <button
          type="button"
          className={peligro ? "btn-danger" : undefined}
          onClick={onConfirmar}
        >
          {textoConfirmar}
        </button>
      </div>
    </dialog>
  );
}
