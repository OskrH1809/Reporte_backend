import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useNavigate } from "react-router";

import {
  crearReporte,
  eliminarReporte,
  listarReportes,
  type Reporte,
} from "../api/reportes";
import { Confirmar, useAvisos } from "../components/Avisos";
import { IconoDescarga, IconoPapelera } from "../components/Iconos";

const MESES = [
  "ene",
  "feb",
  "mar",
  "abr",
  "may",
  "jun",
  "jul",
  "ago",
  "sep",
  "oct",
  "nov",
  "dic",
];

function semanaIso(fecha: Date): { anio: number; semana: number } {
  const dia = new Date(
    Date.UTC(fecha.getFullYear(), fecha.getMonth(), fecha.getDate()),
  );
  const numero = dia.getUTCDay() || 7;
  dia.setUTCDate(dia.getUTCDate() + 4 - numero);
  const inicio = new Date(Date.UTC(dia.getUTCFullYear(), 0, 1));
  return {
    anio: dia.getUTCFullYear(),
    semana: Math.ceil(((dia.getTime() - inicio.getTime()) / 86400000 + 1) / 7),
  };
}

function semanasDelAnio(anio: number): number {
  return semanaIso(new Date(anio, 11, 28)).semana;
}

function rangoSemana(anio: number, semana: number): [Date, Date] {
  const cuatroEnero = new Date(Date.UTC(anio, 0, 4));
  const lunes = new Date(cuatroEnero);
  lunes.setUTCDate(
    cuatroEnero.getUTCDate() - ((cuatroEnero.getUTCDay() || 7) - 1),
  );
  lunes.setUTCDate(lunes.getUTCDate() + (semana - 1) * 7);
  const sabado = new Date(lunes);
  sabado.setUTCDate(lunes.getUTCDate() + 5);
  return [lunes, sabado];
}

function corta(fecha: Date): string {
  return `${String(fecha.getUTCDate()).padStart(2, "0")} ${MESES[fecha.getUTCMonth()]}`;
}

function desdeIso(texto: string): Date {
  const [anio = 2000, mes = 1, dia = 1] = texto.split("-").map(Number);
  return new Date(Date.UTC(anio, mes - 1, dia));
}

function rangoTexto(inicio: Date, fin: Date): string {
  return `${corta(inicio)} – ${corta(fin)} ${fin.getUTCFullYear()}`;
}

function validar(anio: number, semana: number): string | undefined {
  if (!Number.isInteger(anio) || anio < 2000 || anio > 2100)
    return "El año debe estar entre 2000 y 2100.";
  const maximo = semanasDelAnio(anio);
  if (!Number.isInteger(semana) || semana < 1 || semana > maximo)
    return `La semana debe estar entre 1 y ${maximo} para ${anio}.`;
  return undefined;
}

export function Reportes() {
  const actual = semanaIso(new Date());
  const [anio, setAnio] = useState(actual.anio);
  const [semana, setSemana] = useState(actual.semana);
  const [porEliminar, setPorEliminar] = useState<Reporte>();
  const queryClient = useQueryClient();
  const navegar = useNavigate();
  const { avisar } = useAvisos();
  const consulta = useQuery({
    queryKey: ["reportes"],
    queryFn: listarReportes,
  });
  const invalidar = () =>
    queryClient.invalidateQueries({ queryKey: ["reportes"] });
  const crear = useMutation({
    mutationFn: () => crearReporte(anio, semana),
    onSuccess: async (reporte) => {
      avisar(`Reporte ${reporte.codigo} creado.`);
      await invalidar();
      void navegar(`/reportes/${reporte.id}`);
    },
    onError: (error) => avisar(error.message, "error"),
  });
  const eliminar = useMutation({
    mutationFn: (reporte: Reporte) => eliminarReporte(reporte.id),
    onSuccess: (_, reporte) => {
      setPorEliminar(undefined);
      avisar(`Reporte ${reporte.codigo} eliminado.`);
      return invalidar();
    },
    onError: (error) => {
      setPorEliminar(undefined);
      avisar(error.message, "error");
    },
  });

  const reportes = [...(consulta.data ?? [])].sort(
    (a, b) => b.anio - a.anio || b.semana - a.semana,
  );
  const errorFormulario = validar(anio, semana);
  const existente = reportes.find(
    (item) => item.anio === anio && item.semana === semana,
  );
  const rango = errorFormulario ? undefined : rangoSemana(anio, semana);
  const totalHoras = reportes.reduce((suma, r) => suma + r.horas_hombre, 0);

  return (
    <section>
      <header className="page-header">
        <div>
          <h1>Reportes semanales</h1>
          <p className="subtitle">
            {consulta.data
              ? `${reportes.length} ${reportes.length === 1 ? "reporte" : "reportes"} · ${totalHoras.toLocaleString("es")} horas-hombre registradas`
              : "Cargando…"}
          </p>
        </div>
      </header>

      <div className="reportes-layout">
        <form
          className="card nuevo-reporte"
          noValidate
          onSubmit={(event) => {
            event.preventDefault();
            if (!errorFormulario && !existente) crear.mutate();
          }}
        >
          <h2 className="card-title">Nuevo reporte</h2>
          <div className="nuevo-reporte-campos">
            <label className="field">
              <span>Año</span>
              <input
                type="number"
                min={2000}
                max={2100}
                value={Number.isNaN(anio) ? "" : anio}
                aria-invalid={Boolean(errorFormulario?.startsWith("El año"))}
                onChange={(event) => setAnio(event.target.valueAsNumber)}
              />
            </label>
            <label className="field">
              <span>Semana</span>
              <input
                type="number"
                min={1}
                max={53}
                value={Number.isNaN(semana) ? "" : semana}
                aria-invalid={Boolean(errorFormulario?.startsWith("La semana"))}
                onChange={(event) => setSemana(event.target.valueAsNumber)}
              />
            </label>
          </div>
          {errorFormulario ? (
            <p className="field-error" role="alert">
              {errorFormulario}
            </p>
          ) : rango ? (
            <p className="muted">
              Lunes a sábado: <strong>{rangoTexto(...rango)}</strong>
            </p>
          ) : null}
          {existente ? (
            <div className="alert alert-info" role="status">
              <span>
                Ya existe <strong>{existente.codigo}</strong>.
              </span>
              <Link
                className="btn btn-secondary btn-sm"
                to={`/reportes/${existente.id}`}
              >
                Abrir
              </Link>
            </div>
          ) : null}
          <button
            type="submit"
            disabled={
              Boolean(errorFormulario) || Boolean(existente) || crear.isPending
            }
          >
            {crear.isPending ? "Creando…" : "Crear reporte"}
          </button>
        </form>

        <div className="stack">
          {consulta.error ? (
            <p role="alert" className="alert alert-error">
              {consulta.error.message}
            </p>
          ) : null}
          {consulta.isPending ? <p className="empty">Cargando…</p> : null}
          {consulta.data && reportes.length === 0 ? (
            <p className="empty">
              Aún no hay reportes. Crea el de esta semana con el formulario.
            </p>
          ) : null}
          {reportes.length ? (
            <div className="tabla-contenedor">
              <table>
                <thead>
                  <tr>
                    <th>Reporte</th>
                    <th>Fechas</th>
                    <th>Horas-hombre</th>
                    <th>Descargas</th>
                    <th className="acciones">
                      <span className="visualmente-oculto">Acciones</span>
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {reportes.map((reporte) => {
                    const esActual =
                      reporte.anio === actual.anio &&
                      reporte.semana === actual.semana;
                    return (
                      <tr key={reporte.id}>
                        <td>
                          <Link
                            className="enlace-reporte"
                            to={`/reportes/${reporte.id}`}
                          >
                            {reporte.codigo}
                          </Link>
                          <div className="cluster">
                            <span className="muted">
                              Semana {reporte.semana}
                            </span>
                            {esActual ? (
                              <span className="badge">Esta semana</span>
                            ) : null}
                          </div>
                        </td>
                        <td className="num">
                          {rangoTexto(
                            desdeIso(reporte.fecha_inicio),
                            desdeIso(reporte.fecha_fin),
                          )}
                        </td>
                        <td>
                          {reporte.horas_hombre > 0 ? (
                            <span className="badge badge-ok num">
                              {reporte.horas_hombre.toLocaleString("es")} h
                            </span>
                          ) : (
                            <span className="badge badge-warn">
                              Sin capturar
                            </span>
                          )}
                        </td>
                        <td>
                          <div className="row-actions">
                            <a
                              className="btn btn-secondary btn-sm"
                              href={`/api/reportes/${reporte.id}/exportar/formato`}
                              title="Excel con el formato actual"
                            >
                              <IconoDescarga /> Formato
                            </a>
                            <a
                              className="btn btn-secondary btn-sm"
                              href={`/api/reportes/${reporte.id}/exportar/mejorado`}
                              title="Excel mejorado"
                            >
                              <IconoDescarga /> Mejorado
                            </a>
                            <a
                              className="btn btn-secondary btn-sm"
                              href={`/api/reportes/${reporte.id}/exportar/pdf`}
                              title="PDF mejorado"
                            >
                              <IconoDescarga /> PDF
                            </a>
                          </div>
                        </td>
                        <td className="acciones">
                          <div className="row-actions">
                            <Link
                              className="btn btn-sm"
                              to={`/reportes/${reporte.id}`}
                            >
                              Abrir
                            </Link>
                            <button
                              type="button"
                              className="btn-ghost btn-danger btn-icon"
                              aria-label={`Eliminar ${reporte.codigo}`}
                              title="Eliminar"
                              onClick={() => setPorEliminar(reporte)}
                            >
                              <IconoPapelera />
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : null}
        </div>
      </div>

      <Confirmar
        abierto={Boolean(porEliminar)}
        titulo={`¿Eliminar ${porEliminar?.codigo ?? "el reporte"}?`}
        mensaje="Se borrarán sus seis días, actividades y fotos. No se puede deshacer."
        textoConfirmar={eliminar.isPending ? "Eliminando…" : "Eliminar"}
        peligro
        onConfirmar={() => porEliminar && eliminar.mutate(porEliminar)}
        onCancelar={() => setPorEliminar(undefined)}
      />
    </section>
  );
}
