import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { useParams } from "react-router";

import { listarCatalogo } from "../api/catalogos";
import {
  type Actividad,
  type DiaInput,
  editarReporte,
  eliminarFoto,
  guardarDia,
  subirFotos,
  verDia,
  verReporte,
} from "../api/reportes";
import { SelectorColaboradores } from "../components/SelectorColaboradores";
import { SelectorFotos } from "../components/SelectorFotos";
import { TablaCantidades } from "../components/TablaCantidades";
import { calcularHoras } from "../calculos";

const nombres = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"];
const espacios = [
  ["A", "Actividad A", 2],
  ["B", "Actividad B", 4],
  ["C", "Actividad C", 2],
  ["AD", "Antes y después", 4],
] as const;

const vacio: DiaInput = {
  observacion: "",
  texto_fotos: "",
  herramientas: [],
  materiales: [],
  actividades: (["A", "B", "C"] as const).map((letra) => ({
    letra,
    descripcion: "",
    asignaciones: [],
  })),
};

export function EditorReporte() {
  const id = Number(useParams().id);
  const [diaActual, setDiaActual] = useState(0);
  const [borrador, setBorrador] = useState<DiaInput>(vacio);
  const [sucio, setSucio] = useState(false);
  const [errorFotos, setErrorFotos] = useState<Error>();
  const [subiendoEspacio, setSubiendoEspacio] = useState<string>();
  const diaInicializado = useRef<number | undefined>(undefined);
  const queryClient = useQueryClient();
  const reporte = useQuery({
    queryKey: ["reporte", id],
    queryFn: () => verReporte(id),
  });
  const dia = useQuery({
    queryKey: ["dia", id, diaActual],
    queryFn: () => verDia(id, diaActual),
  });
  const colaboradores = useQuery({
    queryKey: ["catalogos", "colaboradores"],
    queryFn: () => listarCatalogo("colaboradores"),
  });
  const herramientas = useQuery({
    queryKey: ["catalogos", "herramientas"],
    queryFn: () => listarCatalogo("herramientas"),
  });
  const materiales = useQuery({
    queryKey: ["catalogos", "materiales"],
    queryFn: () => listarCatalogo("materiales"),
  });
  const firmantes = useQuery({
    queryKey: ["catalogos", "firmantes"],
    queryFn: () => listarCatalogo("firmantes"),
  });
  useEffect(() => {
    if (!dia.data || diaInicializado.current === diaActual) return;
    const datos = dia.data;
    diaInicializado.current = diaActual;
    queueMicrotask(() => {
      const existentes = new Map(
        datos.actividades.map((item) => [item.letra, item]),
      );
      setBorrador({
        observacion: datos.observacion,
        texto_fotos: datos.texto_fotos,
        herramientas: datos.herramientas,
        materiales: datos.materiales,
        actividades: (["A", "B", "C"] as const).map(
          (letra) =>
            existentes.get(letra) ?? {
              letra,
              descripcion: "",
              asignaciones: [],
            },
        ),
      });
      setSucio(false);
    });
  }, [dia.data, diaActual]);
  const guardar = useMutation({
    mutationFn: () =>
      guardarDia(id, diaActual, {
        ...borrador,
        actividades: borrador.actividades.filter(
          (item) => item.descripcion || item.asignaciones.length,
        ),
      }),
    onSuccess: (resultado) => {
      queryClient.setQueryData(["dia", id, diaActual], resultado);
      const existentes = new Map(
        resultado.actividades.map((item) => [item.letra, item]),
      );
      setBorrador({
        observacion: resultado.observacion,
        texto_fotos: resultado.texto_fotos,
        herramientas: resultado.herramientas,
        materiales: resultado.materiales,
        actividades: (["A", "B", "C"] as const).map(
          (letra) =>
            existentes.get(letra) ?? {
              letra,
              descripcion: "",
              asignaciones: [],
            },
        ),
      });
      setSucio(false);
    },
  });
  const editarFirmas = useMutation({
    mutationFn: (valor: {
      elaborado_por_id?: number | null;
      revisado_por_id?: number | null;
    }) => editarReporte(id, valor),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["reporte", id] }),
  });
  const fotos = dia.data?.fotos ?? [];
  const actividadesCalculadas = calcularHoras(
    borrador.actividades,
    diaActual === 5 ? 5 : 8,
  );
  const cambiar = (valor: DiaInput) => {
    setBorrador(valor);
    setSucio(true);
  };
  function cambiarActividad(indice: number, actividad: Actividad) {
    cambiar({
      ...borrador,
      actividades: borrador.actividades.map((item, posicion) =>
        posicion === indice ? actividad : item,
      ),
    });
  }
  function cambiarDia(nuevo: number) {
    if (sucio && !window.confirm("Hay cambios sin guardar. ¿Cambiar de día?"))
      return;
    diaInicializado.current = undefined;
    setDiaActual(nuevo);
  }
  const error =
    reporte.error ??
    dia.error ??
    guardar.error ??
    editarFirmas.error ??
    errorFotos;
  return (
    <section>
      <header className="editor-header">
        <div>
          <h1>{reporte.data?.codigo ?? "Reporte"}</h1>
          <div className="row-actions">
            <a href={`/api/reportes/${id}/exportar/formato`}>Formato actual</a>
            <a href={`/api/reportes/${id}/exportar/mejorado`}>Excel mejorado</a>
            <a href={`/api/reportes/${id}/exportar/pdf`}>PDF</a>
          </div>
        </div>
        <label>
          Elabora
          <select
            value={reporte.data?.elaborado_por_id ?? ""}
            onChange={(event) =>
              editarFirmas.mutate({
                elaborado_por_id: event.target.value
                  ? Number(event.target.value)
                  : null,
              })
            }
          >
            <option value="">Sin seleccionar</option>
            {firmantes.data
              ?.filter((item) => item.tipo === "elabora")
              .map((item) => (
                <option key={item.id} value={item.id}>
                  {item.nombre}
                </option>
              ))}
          </select>
        </label>
        <label>
          Revisa
          <select
            value={reporte.data?.revisado_por_id ?? ""}
            onChange={(event) =>
              editarFirmas.mutate({
                revisado_por_id: event.target.value
                  ? Number(event.target.value)
                  : null,
              })
            }
          >
            <option value="">Sin seleccionar</option>
            {firmantes.data
              ?.filter((item) => item.tipo === "revisa")
              .map((item) => (
                <option key={item.id} value={item.id}>
                  {item.nombre}
                </option>
              ))}
          </select>
        </label>
      </header>
      <div className="tabs" role="tablist">
        {nombres.map((nombre, indice) => (
          <button
            key={nombre}
            type="button"
            role="tab"
            aria-selected={diaActual === indice}
            onClick={() => cambiarDia(indice)}
          >
            {nombre}
          </button>
        ))}
      </div>
      {error ? (
        <p role="alert" className="error-message">
          {error.message}
        </p>
      ) : null}
      {actividadesCalculadas.map((actividad, indice) => (
        <section className="actividad" key={actividad.letra}>
          <h2>Actividad {actividad.letra}</h2>
          <label>
            Descripción
            <textarea
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
            colaboradores={colaboradores.data ?? []}
            valor={actividad.asignaciones}
            onChange={(asignaciones) =>
              cambiarActividad(indice, { ...actividad, asignaciones })
            }
          />
          <p>
            Personas: {actividad.asignaciones.length} · Horas-hombre:{" "}
            {actividad.asignaciones.reduce(
              (total, item) => total + (item.horas ?? 0),
              0,
            )}
          </p>
        </section>
      ))}
      <div className="editor-grid">
        <TablaCantidades
          titulo="Herramientas"
          tipo="herramienta"
          catalogo={herramientas.data ?? []}
          valor={borrador.herramientas}
          onChange={(valor) => cambiar({ ...borrador, herramientas: valor })}
        />
        <TablaCantidades
          titulo="Materiales"
          tipo="material"
          catalogo={materiales.data ?? []}
          valor={borrador.materiales}
          onChange={(valor) => cambiar({ ...borrador, materiales: valor })}
        />
      </div>
      <div className="fotos-secciones">
        {espacios.map(([espacio, etiqueta, maximo]) => (
          <SelectorFotos
            key={espacio}
            espacio={espacio}
            etiqueta={etiqueta}
            maximo={maximo}
            fotos={fotos}
            subiendo={subiendoEspacio === espacio}
            onSubir={(archivos) => {
              setErrorFotos(undefined);
              setSubiendoEspacio(espacio);
              void subirFotos(id, diaActual, espacio, archivos)
                .catch((error: unknown) =>
                  setErrorFotos(
                    error instanceof Error
                      ? error
                      : new Error("Error al subir la foto"),
                  ),
                )
                .finally(() => {
                  setSubiendoEspacio(undefined);
                  void queryClient.invalidateQueries({
                    queryKey: ["dia", id, diaActual],
                  });
                });
            }}
            onEliminar={(fotoId) => {
              setErrorFotos(undefined);
              void eliminarFoto(fotoId)
                .catch((error: unknown) =>
                  setErrorFotos(
                    error instanceof Error
                      ? error
                      : new Error("Error al eliminar la foto"),
                  ),
                )
                .finally(
                  () =>
                    void queryClient.invalidateQueries({
                      queryKey: ["dia", id, diaActual],
                    }),
                );
            }}
          />
        ))}
      </div>
      <label>
        Texto de fotos
        <textarea
          value={borrador.texto_fotos}
          onChange={(event) =>
            cambiar({ ...borrador, texto_fotos: event.target.value })
          }
        />
      </label>
      <label>
        Observación
        <textarea
          value={borrador.observacion}
          onChange={(event) =>
            cambiar({ ...borrador, observacion: event.target.value })
          }
        />
      </label>
      <aside className="totales">
        <strong>
          Personas:{" "}
          {
            new Set(
              actividadesCalculadas.flatMap((actividad) =>
                actividad.asignaciones.map((item) => item.colaborador_id),
              ),
            ).size
          }
        </strong>
        <strong>
          Horas-hombre:{" "}
          {actividadesCalculadas.reduce(
            (total, actividad) =>
              total +
              actividad.asignaciones.reduce(
                (subtotal, item) => subtotal + (item.horas ?? 0),
                0,
              ),
            0,
          )}
        </strong>
        {dia.data?.advertencias.map((aviso) => (
          <p key={aviso}>{aviso}</p>
        ))}
      </aside>
      <button
        type="button"
        disabled={!sucio || guardar.isPending}
        onClick={() => guardar.mutate()}
      >
        Guardar
      </button>
    </section>
  );
}
