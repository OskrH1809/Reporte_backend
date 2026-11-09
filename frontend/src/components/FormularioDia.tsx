import { useEffect, type Dispatch, type SetStateAction } from "react";

import type { Catalogo } from "../api/catalogos";
import type { Actividad, DiaInput, Letra } from "../api/reportes";
import { espaciosFotos, puedeQuitar, siguienteLetra } from "../actividades";
import { calcularHoras } from "../calculos";
import { verificarDia } from "../verificaciones";
import { SelectorColaboradores } from "./SelectorColaboradores";
import { SelectorFotos, type FotoVista } from "./SelectorFotos";
import { TablaCantidades } from "./TablaCantidades";

interface CatalogosFormulario {
  colaboradores: Catalogo[];
  herramientas: Catalogo[];
  materiales: Catalogo[];
}

interface Props {
  dia: DiaInput;
  onChange: (dia: DiaInput) => void;
  jornada: number;
  catalogos: CatalogosFormulario;
  fotos: FotoVista[];
  subiendoEspacio?: Letra | "AD";
  onSubirFotos: (espacio: Letra | "AD", archivos: File[]) => void;
  onEliminarFoto: (id: string | number) => void;
  actividadesAbiertas: Set<Letra>;
  setActividadesAbiertas: Dispatch<SetStateAction<Set<Letra>>>;
  advertencias?: string[];
  onExcesoFotos?: (agregadas: number, limite: number) => void;
  onVerificacion?: (hayErrores: boolean) => void;
}

interface SelectorFirmasProps {
  firmantes: Catalogo[];
  elaboradoPorId: number | null;
  revisadoPorId: number | null;
  onChange: (
    campo: "elaborado_por_id" | "revisado_por_id",
    valor: number | null,
  ) => void;
}

export function SelectorFirmas({
  firmantes,
  elaboradoPorId,
  revisadoPorId,
  onChange,
}: SelectorFirmasProps) {
  const faltanFirmas = !elaboradoPorId || !revisadoPorId;
  return (
    <section className="card firmas-card">
      <div className="card-header">
        <h2 className="card-title">Firmas</h2>
        {faltanFirmas ? (
          <span className="badge badge-warn">Faltan firmas</span>
        ) : null}
      </div>
      <div className="grid-2">
        {(["elabora", "revisa"] as const).map((tipo) => {
          const campo =
            tipo === "elabora" ? "elaborado_por_id" : "revisado_por_id";
          const valor = tipo === "elabora" ? elaboradoPorId : revisadoPorId;
          return (
            <label className="field" key={tipo}>
              <span>{tipo === "elabora" ? "Elabora" : "Revisa"}</span>
              <select
                value={valor ?? ""}
                onChange={(event) =>
                  onChange(
                    campo,
                    event.target.value ? Number(event.target.value) : null,
                  )
                }
              >
                <option value="">Sin seleccionar</option>
                {firmantes
                  .filter((item) => item.tipo === tipo)
                  .map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.nombre}
                    </option>
                  ))}
              </select>
            </label>
          );
        })}
      </div>
    </section>
  );
}

export function FormularioDia({
  dia,
  onChange,
  jornada,
  catalogos,
  fotos,
  subiendoEspacio,
  onSubirFotos,
  onEliminarFoto,
  actividadesAbiertas,
  setActividadesAbiertas,
  advertencias = [],
  onExcesoFotos,
  onVerificacion,
}: Props) {
  const actividades = calcularHoras(dia.actividades, jornada);
  const nombres = new Map(
    catalogos.colaboradores.map((item) => [item.id, item.nombre]),
  );
  const verificaciones = verificarDia({
    actividades,
    herramientas: dia.herramientas,
    materiales: dia.materiales,
    fotos,
    observacion: dia.observacion,
    jornada,
    nombres,
  });
  const hayErrores = verificaciones.some((item) => item.nivel === "error");
  useEffect(() => onVerificacion?.(hayErrores), [hayErrores, onVerificacion]);

  function cambiarActividad(indice: number, actividad: Actividad) {
    onChange({
      ...dia,
      actividades: dia.actividades.map((item, posicion) =>
        posicion === indice ? actividad : item,
      ),
    });
  }

  function agregarActividad() {
    const letra = siguienteLetra(dia.actividades);
    if (!letra) return;
    onChange({
      ...dia,
      actividades: [
        ...dia.actividades,
        { letra, descripcion: "", asignaciones: [] },
      ],
    });
    setActividadesAbiertas((actuales) => new Set(actuales).add(letra));
  }

  function quitarActividad(actividad: Actividad) {
    onChange({
      ...dia,
      actividades: dia.actividades.filter(
        (item) => item.letra !== actividad.letra,
      ),
    });
    setActividadesAbiertas((actuales) => {
      const nuevas = new Set(actuales);
      nuevas.delete(actividad.letra);
      return nuevas;
    });
  }

  const proximaLetra = siguienteLetra(dia.actividades);
  return (
    <>
      <div className="actividades-stack">
        {actividades.map((actividad, indice) => {
          const vacia =
            !actividad.descripcion && actividad.asignaciones.length === 0;
          const abierta = !vacia || actividadesAbiertas.has(actividad.letra);
          const sePuedeQuitar = puedeQuitar(
            actividad,
            indice === actividades.length - 1,
            fotos,
          );
          const horas = actividad.asignaciones.reduce(
            (total, item) => total + (item.horas ?? 0),
            0,
          );
          if (!abierta) {
            return (
              <section className="card actividad-plegada" key={actividad.letra}>
                <strong>
                  Actividad {actividad.letra} ·{" "}
                  <span className="muted">sin capturar</span>
                </strong>
                <div className="cluster">
                  {sePuedeQuitar ? (
                    <button
                      type="button"
                      className="btn-secondary btn-sm"
                      onClick={() => quitarActividad(actividad)}
                    >
                      Quitar
                    </button>
                  ) : null}
                  <button
                    type="button"
                    className="btn-secondary btn-sm"
                    onClick={() =>
                      setActividadesAbiertas((actuales) =>
                        new Set(actuales).add(actividad.letra),
                      )
                    }
                  >
                    Capturar
                  </button>
                </div>
              </section>
            );
          }
          return (
            <section className="card actividad-card" key={actividad.letra}>
              <div className="card-header">
                <h2 className="card-title">Actividad {actividad.letra}</h2>
                <div className="cluster">
                  <span className="badge badge-muted">
                    {actividad.asignaciones.length} personas
                  </span>
                  <span className="badge badge-muted num">
                    {horas.toLocaleString("es")} h-h
                  </span>
                  {sePuedeQuitar ? (
                    <button
                      type="button"
                      className="btn-secondary btn-sm"
                      onClick={() => quitarActividad(actividad)}
                    >
                      Quitar
                    </button>
                  ) : null}
                </div>
              </div>
              <label className="field">
                <span>Descripción</span>
                <textarea
                  rows={3}
                  value={actividad.descripcion}
                  onChange={(event) =>
                    cambiarActividad(indice, {
                      ...actividad,
                      descripcion: event.target.value,
                    })
                  }
                />
              </label>
              <SelectorColaboradores
                colaboradores={catalogos.colaboradores}
                valor={actividad.asignaciones}
                onChange={(asignaciones) =>
                  cambiarActividad(indice, { ...actividad, asignaciones })
                }
              />
            </section>
          );
        })}
      </div>
      <button
        type="button"
        className="btn-secondary"
        disabled={proximaLetra === undefined}
        title={
          proximaLetra === undefined
            ? "Máximo 10 actividades por día"
            : undefined
        }
        onClick={agregarActividad}
      >
        Agregar actividad
      </button>

      <div className="grid-2">
        <TablaCantidades
          titulo="Herramientas"
          tipo="herramienta"
          catalogo={catalogos.herramientas}
          valor={dia.herramientas}
          onChange={(valor) => onChange({ ...dia, herramientas: valor })}
        />
        <TablaCantidades
          titulo="Materiales"
          tipo="material"
          catalogo={catalogos.materiales}
          valor={dia.materiales}
          onChange={(valor) => onChange({ ...dia, materiales: valor })}
        />
      </div>

      <section className="card">
        <div className="card-header">
          <h2 className="card-title">Fotos</h2>
        </div>
        <div className="fotos-secciones">
          {espaciosFotos(dia.actividades).map(([espacio, etiqueta, maximo]) => (
            <SelectorFotos
              key={espacio}
              espacio={espacio}
              etiqueta={etiqueta}
              maximo={maximo}
              fotos={fotos}
              subiendo={subiendoEspacio === espacio}
              onExceso={onExcesoFotos}
              onSubir={(archivos) => onSubirFotos(espacio, archivos)}
              onEliminar={onEliminarFoto}
            />
          ))}
        </div>
      </section>

      <div className="grid-2 textos-dia">
        <label className="field card">
          <span>Texto de fotos</span>
          <textarea
            rows={3}
            value={dia.texto_fotos}
            onChange={(event) =>
              onChange({ ...dia, texto_fotos: event.target.value })
            }
          />
        </label>
        <label className="field card">
          <span>Observación</span>
          <textarea
            rows={3}
            value={dia.observacion}
            onChange={(event) =>
              onChange({ ...dia, observacion: event.target.value })
            }
          />
        </label>
      </div>

      <section className="card verificacion-card">
        <div className="card-header">
          <h2 className="card-title">Verificación</h2>
        </div>
        {verificaciones.length === 0 && advertencias.length === 0 ? (
          <p className="alert alert-ok" role="status">
            Todo listo para guardar.
          </p>
        ) : (
          <div className="stack avisos-verificacion">
            {verificaciones.map((item, indice) => (
              <p
                key={`${item.seccion}-${item.mensaje}-${indice}`}
                className={`alert ${item.nivel === "error" ? "alert-error" : "alert-warn"}`}
                role={item.nivel === "error" ? "alert" : "status"}
              >
                {item.mensaje}
              </p>
            ))}
            {advertencias.map((aviso) => (
              <p key={aviso} className="alert alert-warn" role="status">
                {aviso}
              </p>
            ))}
          </div>
        )}
      </section>
    </>
  );
}
