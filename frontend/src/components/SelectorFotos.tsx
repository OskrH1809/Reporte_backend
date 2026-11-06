import type { Foto } from "../api/reportes";

interface Props {
  espacio: Foto["espacio"];
  etiqueta: string;
  maximo: number;
  fotos: Foto[];
  onSubir: (archivo: File) => void;
  onEliminar: (id: number) => void;
}

export function SelectorFotos({
  espacio,
  etiqueta,
  maximo,
  fotos,
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
        accept="image/jpeg,image/png,image/webp"
        disabled={propias.length >= maximo}
        onChange={(event) => {
          const archivo = event.target.files?.[0];
          if (archivo) onSubir(archivo);
          event.target.value = "";
        }}
      />
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
