import type { Catalogo } from "../api/catalogos";
import type { Asignacion } from "../api/reportes";

interface Props {
  colaboradores: Catalogo[];
  valor: Asignacion[];
  onChange: (valor: Asignacion[]) => void;
}

export function SelectorColaboradores({
  colaboradores,
  valor,
  onChange,
}: Props) {
  function alternar(colaborador: Catalogo) {
    const existe = valor.some((item) => item.colaborador_id === colaborador.id);
    onChange(
      existe
        ? valor.filter((item) => item.colaborador_id !== colaborador.id)
        : [
            ...valor,
            {
              colaborador_id: colaborador.id,
              colaborador_nombre: colaborador.nombre,
              horas_manual: false,
            },
          ],
    );
  }
  function actualizar(id: number, cambio: Partial<Asignacion>) {
    onChange(
      valor.map((item) =>
        item.colaborador_id === id ? { ...item, ...cambio } : item,
      ),
    );
  }
  return (
    <div className="selector-colaboradores">
      <div className="chips">
        {colaboradores.map((colaborador) => (
          <button
            key={colaborador.id}
            type="button"
            className={
              valor.some((item) => item.colaborador_id === colaborador.id)
                ? "chip activo"
                : "chip"
            }
            aria-pressed={valor.some(
              (item) => item.colaborador_id === colaborador.id,
            )}
            onClick={() => alternar(colaborador)}
          >
            {colaborador.nombre}
          </button>
        ))}
      </div>
      <div className="horas-grid">
        {valor.map((asignacion) => (
          <div className="horas-persona" key={asignacion.colaborador_id}>
            <span>
              {asignacion.colaborador_nombre ??
                colaboradores.find(
                  (item) => item.id === asignacion.colaborador_id,
                )?.nombre}
            </span>
            <label className="horas-campo">
              <span>Horas</span>
              <input
                aria-label={`Horas de ${asignacion.colaborador_nombre ?? asignacion.colaborador_id}`}
                type="number"
                min={0}
                max={24}
                step="0.25"
                value={asignacion.horas ?? ""}
                onChange={(event) =>
                  actualizar(asignacion.colaborador_id, {
                    horas: event.target.value
                      ? Number(event.target.value)
                      : undefined,
                    horas_manual: Boolean(event.target.value),
                  })
                }
              />
            </label>
            <label className="manual-campo">
              <input
                type="checkbox"
                checked={asignacion.horas_manual}
                onChange={(event) =>
                  actualizar(asignacion.colaborador_id, {
                    horas_manual: event.target.checked,
                  })
                }
              />
              Manual
            </label>
          </div>
        ))}
      </div>
    </div>
  );
}
