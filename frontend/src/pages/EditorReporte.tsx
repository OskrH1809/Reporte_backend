import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { useParams } from "react-router";

import { listarCatalogo } from "../api/catalogos";
import {
  type Actividad,
  type DiaInput,
  type Foto,
  editarReporte,
  eliminarFoto,
  guardarDia,
  subirFotos,
  verDia,
  verReporte,
} from "../api/reportes";
import {
  armarActividades,
  espaciosFotos,
  puedeQuitar,
  siguienteLetra,
} from "../actividades";
import { calcularHoras } from "../calculos";
import { Confirmar, useAvisos } from "../components/Avisos";
import { SelectorColaboradores } from "../components/SelectorColaboradores";
import { SelectorFotos } from "../components/SelectorFotos";
import { TablaCantidades } from "../components/TablaCantidades";
import { verificarDia } from "../verificaciones";
import "../editor.css";

const nombres = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"];
const nombresCortos = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb"];

const vacio: DiaInput = {
  observacion: "",
  texto_fotos: "",
  herramientas: [],
  materiales: [],
  actividades: armarActividades([]),
};

const mensajeError = (error: unknown, alternativo: string) =>
  error instanceof Error ? error.message : alternativo;

function fechaDia(fechaInicio: string | undefined, desplazamiento: number) {
  if (!fechaInicio) return "";
  const fecha = new Date(`${fechaInicio}T00:00:00`);
  fecha.setDate(fecha.getDate() + desplazamiento);
  return fecha.toLocaleDateString("es", { day: "2-digit", month: "2-digit" });
}

function fechaLarga(iso: string): string {
  const [anio, mes, dia] = iso.split("-");
  return `${dia}/${mes}/${anio}`;
}

export function EditorReporte() {
  const id = Number(useParams().id);
  const [diaActual, setDiaActual] = useState(0);
  const [borrador, setBorrador] = useState<DiaInput>(vacio);
  const [sucio, setSucio] = useState(false);
  const [subiendoEspacio, setSubiendoEspacio] = useState<string>();
  const [fotoPendiente, setFotoPendiente] = useState<Foto>();
  const [diaPendiente, setDiaPendiente] = useState<number>();
  const [actividadesAbiertas, setActividadesAbiertas] = useState(
    new Set<Actividad["letra"]>(),
  );
  const diaInicializado = useRef<number | undefined>(undefined);
  const queryClient = useQueryClient();
  const { avisar } = useAvisos();
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
      setBorrador({
        observacion: datos.observacion,
        texto_fotos: datos.texto_fotos,
        herramientas: datos.herramientas,
        materiales: datos.materiales,
        actividades: armarActividades(datos.actividades),
      });
      setActividadesAbiertas(
        new Set(
          datos.actividades
            .filter(
              (actividad) =>
                actividad.descripcion || actividad.asignaciones.length,
            )
            .map((actividad) => actividad.letra),
        ),
      );
      setSucio(false);
    });
  }, [dia.data, diaActual]);

  useEffect(() => {
    if (!sucio) return;
    const prevenirSalida = (event: BeforeUnloadEvent) => event.preventDefault();
    window.addEventListener("beforeunload", prevenirSalida);
    return () => window.removeEventListener("beforeunload", prevenirSalida);
  }, [sucio]);

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
      setBorrador({
        observacion: resultado.observacion,
        texto_fotos: resultado.texto_fotos,
        herramientas: resultado.herramientas,
        materiales: resultado.materiales,
        actividades: armarActividades(resultado.actividades),
      });
      setSucio(false);
      avisar("Día guardado.");
    },
    onError: (error) =>
      avisar(mensajeError(error, "Error al guardar el día."), "error"),
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
  const jornada = diaActual === 5 ? 5 : 8;
  const actividadesCalculadas = calcularHoras(borrador.actividades, jornada);
  const nombresColaboradores = new Map(
    (colaboradores.data ?? []).map((item) => [item.id, item.nombre]),
  );
  const verificaciones = verificarDia({
    actividades: actividadesCalculadas,
    herramientas: borrador.herramientas,
    materiales: borrador.materiales,
    fotos,
    observacion: borrador.observacion,
    jornada,
    nombres: nombresColaboradores,
  });
  const hayErrores = verificaciones.some((item) => item.nivel === "error");
  const personas = new Set(
    actividadesCalculadas.flatMap((actividad) =>
      actividad.asignaciones.map((item) => item.colaborador_id),
    ),
  ).size;
  const horasHombre = actividadesCalculadas.reduce(
    (total, actividad) =>
      total +
      actividad.asignaciones.reduce(
        (subtotal, item) => subtotal + (item.horas ?? 0),
        0,
      ),
    0,
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
  function agregarActividad() {
    const letra = siguienteLetra(borrador.actividades);
    if (!letra) return;
    cambiar({
      ...borrador,
      actividades: [
        ...borrador.actividades,
        { letra, descripcion: "", asignaciones: [] },
      ],
    });
    setActividadesAbiertas((actuales) => new Set(actuales).add(letra));
  }
  function quitarActividad(actividad: Actividad) {
    cambiar({
      ...borrador,
      actividades: borrador.actividades.filter(
        (item) => item.letra !== actividad.letra,
      ),
    });
    setActividadesAbiertas((actuales) => {
      const nuevas = new Set(actuales);
      nuevas.delete(actividad.letra);
      return nuevas;
    });
  }
  function confirmarCambioDia(nuevo: number) {
    diaInicializado.current = undefined;
    setDiaActual(nuevo);
    setDiaPendiente(undefined);
  }
  function cambiarDia(nuevo: number) {
    if (nuevo === diaActual) return;
    if (sucio) {
      setDiaPendiente(nuevo);
      return;
    }
    confirmarCambioDia(nuevo);
  }
  function eliminarFotoConfirmada() {
    if (!fotoPendiente) return;
    const foto = fotoPendiente;
    setFotoPendiente(undefined);
    void eliminarFoto(foto.id)
      .then(() => {
        avisar("Foto eliminada.");
        return queryClient.invalidateQueries({
          queryKey: ["dia", id, diaActual],
        });
      })
      .catch((error: unknown) =>
        avisar(mensajeError(error, "Error al eliminar la foto."), "error"),
      );
  }

  const error = reporte.error ?? dia.error ?? editarFirmas.error;
  const faltanFirmas =
    !reporte.data?.elaborado_por_id || !reporte.data.revisado_por_id;
  const proximaLetra = siguienteLetra(borrador.actividades);
  return (
    <section className="editor stack">
      <header className="page-header">
        <div>
          <h1>{reporte.data?.codigo ?? "Reporte"}</h1>
          <p className="subtitle">
            {reporte.data
              ? `${fechaLarga(reporte.data.fecha_inicio)} – ${fechaLarga(reporte.data.fecha_fin)}`
              : "Cargando fechas…"}
          </p>
        </div>
        <div className="cluster">
          <a
            className="btn btn-secondary btn-sm"
            href={`/api/reportes/${id}/exportar/formato`}
          >
            Formato actual
          </a>
          <a
            className="btn btn-secondary btn-sm"
            href={`/api/reportes/${id}/exportar/mejorado`}
          >
            Excel mejorado
          </a>
          <a
            className="btn btn-secondary btn-sm"
            href={`/api/reportes/${id}/exportar/pdf`}
          >
            PDF
          </a>
        </div>
      </header>

      <section className="card firmas-card">
        <div className="card-header">
          <h2 className="card-title">Firmas</h2>
          {faltanFirmas ? (
            <span className="badge badge-warn">Faltan firmas</span>
          ) : null}
        </div>
        <div className="grid-2">
          <label className="field">
            <span>Elabora</span>
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
          <label className="field">
            <span>Revisa</span>
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
        </div>
      </section>

      <div className="segmented dias-tabs" role="tablist">
        {nombres.map((nombre, indice) => (
          <button
            key={nombre}
            type="button"
            role="tab"
            aria-selected={diaActual === indice}
            onClick={() => cambiarDia(indice)}
          >
            <span className="dia-completo">{nombre}</span>
            <span className="dia-corto">{nombresCortos[indice]}</span>
            <small>{fechaDia(reporte.data?.fecha_inicio, indice)}</small>
          </button>
        ))}
      </div>

      {error ? (
        <p role="alert" className="alert alert-error">
          {error.message}
        </p>
      ) : null}

      <div className="actividades-stack">
        {actividadesCalculadas.map((actividad, indice) => {
          const vacia =
            !actividad.descripcion && actividad.asignaciones.length === 0;
          const abierta = !vacia || actividadesAbiertas.has(actividad.letra);
          const sePuedeQuitar = puedeQuitar(
            actividad,
            indice === actividadesCalculadas.length - 1,
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
                colaboradores={colaboradores.data ?? []}
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

      <section className="card">
        <div className="card-header">
          <h2 className="card-title">Fotos</h2>
        </div>
        <div className="fotos-secciones">
          {espaciosFotos(borrador.actividades).map(
            ([espacio, etiqueta, maximo]) => (
              <SelectorFotos
                key={espacio}
                espacio={espacio}
                etiqueta={etiqueta}
                maximo={maximo}
                fotos={fotos}
                subiendo={subiendoEspacio === espacio}
                onExceso={(agregadas, limite) =>
                  avisar(
                    `Solo se agregaron ${agregadas} foto(s); el máximo es ${limite}.`,
                    "info",
                  )
                }
                onSubir={(archivos) => {
                  setSubiendoEspacio(espacio);
                  void subirFotos(id, diaActual, espacio, archivos)
                    .then(() => {
                      avisar("Foto subida.");
                      return queryClient.invalidateQueries({
                        queryKey: ["dia", id, diaActual],
                      });
                    })
                    .catch((error: unknown) =>
                      avisar(
                        mensajeError(error, "Error al subir la foto."),
                        "error",
                      ),
                    )
                    .finally(() => setSubiendoEspacio(undefined));
                }}
                onEliminar={(fotoId) =>
                  setFotoPendiente(fotos.find((foto) => foto.id === fotoId))
                }
              />
            ),
          )}
        </div>
      </section>

      <div className="grid-2 textos-dia">
        <label className="field card">
          <span>Texto de fotos</span>
          <textarea
            rows={3}
            value={borrador.texto_fotos}
            onChange={(event) =>
              cambiar({ ...borrador, texto_fotos: event.target.value })
            }
          />
        </label>
        <label className="field card">
          <span>Observación</span>
          <textarea
            rows={3}
            value={borrador.observacion}
            onChange={(event) =>
              cambiar({ ...borrador, observacion: event.target.value })
            }
          />
        </label>
      </div>

      <section className="card verificacion-card">
        <div className="card-header">
          <h2 className="card-title">Verificación</h2>
        </div>
        {verificaciones.length === 0 && !dia.data?.advertencias.length ? (
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
            {dia.data?.advertencias.map((aviso) => (
              <p key={aviso} className="alert alert-warn" role="status">
                {aviso}
              </p>
            ))}
          </div>
        )}
      </section>

      <aside className="sticky-bar">
        <strong className="num">
          Personas {personas} · Horas-hombre {horasHombre.toLocaleString("es")}{" "}
          · jornada {jornada} h
        </strong>
        <div className="cluster">
          {sucio ? (
            <span className="badge badge-warn">Cambios sin guardar</span>
          ) : null}
          <button
            type="button"
            disabled={!sucio || guardar.isPending || hayErrores}
            title={
              hayErrores
                ? "Corrige los errores de verificación antes de guardar."
                : undefined
            }
            onClick={() => guardar.mutate()}
          >
            Guardar
          </button>
        </div>
      </aside>

      <Confirmar
        abierto={diaPendiente !== undefined}
        titulo="Cambiar de día"
        mensaje="Hay cambios sin guardar. ¿Cambiar de día?"
        textoConfirmar="Cambiar de día"
        onConfirmar={() => {
          if (diaPendiente !== undefined) confirmarCambioDia(diaPendiente);
        }}
        onCancelar={() => setDiaPendiente(undefined)}
      />
      <Confirmar
        abierto={Boolean(fotoPendiente)}
        titulo="Eliminar foto"
        mensaje={`¿Eliminar ${fotoPendiente?.nombre_original ?? "esta foto"}?`}
        textoConfirmar="Eliminar"
        peligro
        onConfirmar={eliminarFotoConfirmada}
        onCancelar={() => setFotoPendiente(undefined)}
      />
    </section>
  );
}
