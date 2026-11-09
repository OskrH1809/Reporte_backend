import type { Letra } from "../api/reportes";

export interface FotoVista {
  id: string | number;
  espacio: Letra | "AD";
  url: string;
  nombre_original: string;
  orden?: number;
}

interface Props {
  espacio: Letra | "AD";
  etiqueta: string;
  maximo: number;
  fotos: FotoVista[];
  subiendo?: boolean;
  onSubir: (archivos: File[]) => void;
  onEliminar: (id: string | number) => void;
  onExceso?: (agregadas: number, maximo: number) => void;
}

export function SelectorFotos({
  espacio,
  etiqueta,
  maximo,
  fotos,
  subiendo = false,
  onSubir,
  onEliminar,
  onExceso,
}: Props) {
  const propias = fotos.filter((foto) => foto.espacio === espacio);
  return (
    <section className="selector-fotos">
      <div className="selector-fotos-titulo">
        <h3>{etiqueta}</h3>
        <span
          className={`badge ${propias.length === maximo ? "badge-ok" : "badge-muted"}`}
        >
          {propias.length}/{maximo}
        </span>
      </div>
      <div className="fotos-grid">
        {propias.map((foto) => (
          <figure key={foto.id}>
            <img src={foto.url} alt={foto.nombre_original} />
            <button
              type="button"
              className="btn-icon"
              aria-label={`Eliminar foto ${foto.nombre_original}`}
              onClick={() => onEliminar(foto.id)}
            >
              ×
            </button>
          </figure>
        ))}
      </div>
      <label className="btn btn-secondary btn-sm carga-fotos">
        Agregar fotos
        <input
          aria-label={`Fotos ${etiqueta}`}
          type="file"
          multiple
          accept="image/jpeg,image/png,image/webp"
          disabled={propias.length >= maximo || subiendo}
          onChange={(event) => {
            const seleccionados = Array.from(event.target.files ?? []);
            const disponibles = maximo - propias.length;
            const archivos = seleccionados.slice(0, disponibles);
            if (seleccionados.length > disponibles)
              onExceso?.(archivos.length, maximo);
            if (archivos.length) onSubir(archivos);
            event.target.value = "";
          }}
        />
      </label>
      {subiendo ? <p role="status">Subiendo…</p> : null}
    </section>
  );
}
