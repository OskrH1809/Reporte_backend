import type { Catalogo } from "../api/catalogos";
import type { Cantidad } from "../api/reportes";

interface Props {
  titulo: string;
  catalogo: Catalogo[];
  tipo: "herramienta" | "material";
  valor: Cantidad[];
  onChange: (valor: Cantidad[]) => void;
}

export function TablaCantidades({
  titulo,
  catalogo,
  tipo,
  valor,
  onChange,
}: Props) {
  const campo = tipo === "material" ? "material_id" : "herramienta_id";
  const usados = new Set(valor.map((item) => item[campo]));
  function agregar(id: number) {
    if (!id || usados.has(id)) return;
    onChange([...valor, { [campo]: id, cantidad: 1 }]);
  }
  return (
    <section className="cantidades">
      <h3>{titulo}</h3>
      <select
        aria-label={`Agregar ${titulo.toLowerCase()}`}
        value=""
        onChange={(event) => agregar(Number(event.target.value))}
      >
        <option value="">Agregar…</option>
        {catalogo
          .filter((item) => !usados.has(item.id))
          .map((item) => (
            <option key={item.id} value={item.id}>
              {item.nombre}
              {item.unidad ? ` (${item.unidad})` : ""}
            </option>
          ))}
      </select>
      {valor.map((cantidad) => {
        const id = cantidad[campo];
        const item = catalogo.find((entrada) => entrada.id === id);
        return (
          <div className="cantidad-fila" key={id}>
            <span>
              {item?.nombre}
              {item?.unidad ? ` · ${item.unidad}` : ""}
            </span>
            <input
              aria-label={`Cantidad de ${item?.nombre ?? id}`}
              type="number"
              min={0.01}
              step="0.01"
              value={cantidad.cantidad}
              onChange={(event) =>
                onChange(
                  valor.map((entrada) =>
                    entrada[campo] === id
                      ? { ...entrada, cantidad: Number(event.target.value) }
                      : entrada,
                  ),
                )
              }
            />
            <button
              type="button"
              onClick={() =>
                onChange(valor.filter((entrada) => entrada[campo] !== id))
              }
            >
              Quitar
            </button>
          </div>
        );
      })}
    </section>
  );
}
