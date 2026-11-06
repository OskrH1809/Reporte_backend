import type { Foto } from "../api/reportes";

interface Props {
  espacio: Foto["espacio"];
  etiqueta: string;
  maximo: number;
  fotos: Foto[];
  subiendo?: boolean;
  onSubir: (archivos: File[]) => void;
  onEliminar: (id: number) => void;
}

export function SelectorFotos({
  espacio,
  etiqueta,
  maximo,
  fotos,
  subiendo = false,
  onSubir,
  onEliminar,
}: Props) {
  const propias = fotos.filter((foto) => foto.espacio === espacio);
  return (
    <section className="selector-fotos">
      <h3>
        {etiqueta}{" "}
        <span>
          {propias.length}/{maximo}
        </span>
      </h3>
      <input
        aria-label={`Fotos ${etiqueta}`}
        type="file"
        multiple
        accept="image/jpeg,image/png,image/webp"
        disabled={propias.length >= maximo || subiendo}
        onChange={(event) => {
          const disponibles = maximo - propias.length;
          const archivos = Array.from(event.target.files ?? []).slice(
            0,
            disponibles,
          );
          if (archivos.length) onSubir(archivos);
          event.target.value = "";
        }}
      />
      {subiendo ? <p>Subiendo…</p> : null}
      <div className="fotos-grid">
        {propias.map((foto) => (
          <figure key={foto.id}>
            <img src={foto.url} alt={foto.nombre_original} />
            <button type="button" onClick={() => onEliminar(foto.id)}>
              Eliminar
            </button>
          </figure>
        ))}
      </div>
    </section>
  );
}
