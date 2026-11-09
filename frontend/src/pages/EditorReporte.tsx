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
import { armarActividades } from "../actividades";
import { calcularHoras } from "../calculos";
import { Confirmar, useAvisos } from "../components/Avisos";
import { FormularioDia, SelectorFirmas } from "../components/FormularioDia";
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
  const [hayErrores, setHayErrores] = useState(false);
  const [subiendoEspacio, setSubiendoEspacio] = useState<Foto["espacio"]>();
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
        actividades: armarActividades(datos.actividades, datos.fotos),
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
        actividades: armarActividades(resultado.actividades, resultado.fotos),
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
  function confirmarCambioDia(nuevo: number) {
    diaInicializado.current = undefined;
    setDiaActual(nuevo);
    setDiaPendiente(undefined);
  }
  function cambiarDia(nuevo: number) {
    if (nuevo === diaActual) return;
    if (sucio) setDiaPendiente(nuevo);
    else confirmarCambioDia(nuevo);
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

      <SelectorFirmas
        firmantes={firmantes.data ?? []}
        elaboradoPorId={reporte.data?.elaborado_por_id ?? null}
        revisadoPorId={reporte.data?.revisado_por_id ?? null}
        onChange={(campo, valor) => editarFirmas.mutate({ [campo]: valor })}
      />

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

      <FormularioDia
        dia={borrador}
        onChange={cambiar}
        jornada={jornada}
        catalogos={{
          colaboradores: colaboradores.data ?? [],
          herramientas: herramientas.data ?? [],
          materiales: materiales.data ?? [],
        }}
        fotos={fotos}
        subiendoEspacio={subiendoEspacio}
        onSubirFotos={(espacio, archivos) => {
          setSubiendoEspacio(espacio);
          void subirFotos(id, diaActual, espacio, archivos)
            .then(() => {
              avisar("Foto subida.");
              return queryClient.invalidateQueries({
                queryKey: ["dia", id, diaActual],
              });
            })
            .catch((error: unknown) =>
              avisar(mensajeError(error, "Error al subir la foto."), "error"),
            )
            .finally(() => setSubiendoEspacio(undefined));
        }}
        onEliminarFoto={(fotoId) =>
          setFotoPendiente(fotos.find((foto) => foto.id === fotoId))
        }
        actividadesAbiertas={actividadesAbiertas}
        setActividadesAbiertas={setActividadesAbiertas}
        advertencias={dia.data?.advertencias}
        onExcesoFotos={(agregadas, limite) =>
          avisar(
            `Solo se agregaron ${agregadas} foto(s); el máximo es ${limite}.`,
            "info",
          )
        }
        onVerificacion={setHayErrores}
      />

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
        onConfirmar={() =>
          diaPendiente !== undefined && confirmarCambioDia(diaPendiente)
        }
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
