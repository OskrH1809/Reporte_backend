import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router";

import { crearReporte, eliminarReporte, listarReportes } from "../api/reportes";

function semanaActual(): { anio: number; semana: number } {
  const hoy = new Date();
  const fecha = new Date(
    Date.UTC(hoy.getFullYear(), hoy.getMonth(), hoy.getDate()),
  );
  const dia = fecha.getUTCDay() || 7;
  fecha.setUTCDate(fecha.getUTCDate() + 4 - dia);
  const inicio = new Date(Date.UTC(fecha.getUTCFullYear(), 0, 1));
  return {
    anio: fecha.getUTCFullYear(),
    semana: Math.ceil(
      ((fecha.getTime() - inicio.getTime()) / 86400000 + 1) / 7,
    ),
  };
}

export function Reportes() {
  const actual = semanaActual();
  const [anio, setAnio] = useState(actual.anio);
  const [semana, setSemana] = useState(actual.semana);
  const [confirmando, setConfirmando] = useState<number>();
  const queryClient = useQueryClient();
  const consulta = useQuery({
    queryKey: ["reportes"],
    queryFn: listarReportes,
  });
  const invalidar = () =>
    queryClient.invalidateQueries({ queryKey: ["reportes"] });
  const crear = useMutation({
    mutationFn: () => crearReporte(anio, semana),
    onSuccess: invalidar,
  });
  const eliminar = useMutation({
    mutationFn: eliminarReporte,
    onSuccess: () => {
      setConfirmando(undefined);
      return invalidar();
    },
  });
  const error = consulta.error ?? crear.error ?? eliminar.error;
  return (
    <section>
      <h1>Reportes semanales</h1>
      <form
        className="inline-form"
        onSubmit={(event) => {
          event.preventDefault();
          crear.mutate();
        }}
      >
        <label>
          Año
          <input
            type="number"
            min={2000}
            max={2100}
            value={anio}
            onChange={(event) => setAnio(Number(event.target.value))}
          />
        </label>
        <label>
          Semana
          <input
            type="number"
            min={1}
            max={53}
            value={semana}
            onChange={(event) => setSemana(Number(event.target.value))}
          />
        </label>
        <button type="submit">Crear reporte</button>
      </form>
      {error ? (
        <p role="alert" className="error-message">
          {error.message}
        </p>
      ) : null}
      {consulta.data ? (
        <table>
          <thead>
            <tr>
              <th>Semana</th>
              <th>Fechas</th>
              <th>Horas</th>
              <th>Descargas</th>
              <th>Acciones</th>
            </tr>
          </thead>
          <tbody>
            {consulta.data.map((reporte) => (
              <tr key={reporte.id}>
                <td>
                  <Link to={`/reportes/${reporte.id}`}>{reporte.codigo}</Link>
                </td>
                <td>
                  {reporte.fecha_inicio} — {reporte.fecha_fin}
                </td>
                <td>{reporte.horas_hombre}</td>
                <td className="row-actions">
                  <a href={`/api/reportes/${reporte.id}/exportar/formato`}>
                    Formato
                  </a>
                  <a href={`/api/reportes/${reporte.id}/exportar/mejorado`}>
                    Mejorado
                  </a>
                  <a href={`/api/reportes/${reporte.id}/exportar/pdf`}>PDF</a>
                </td>
                <td>
                  {confirmando === reporte.id ? (
                    <span className="row-actions">
                      ¿Eliminar?
                      <button
                        type="button"
                        onClick={() => eliminar.mutate(reporte.id)}
                      >
                        Sí
                      </button>
                      <button
                        type="button"
                        onClick={() => setConfirmando(undefined)}
                      >
                        No
                      </button>
                    </span>
                  ) : (
                    <button
                      type="button"
                      onClick={() => setConfirmando(reporte.id)}
                    >
                      Eliminar
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : null}
    </section>
  );
}
