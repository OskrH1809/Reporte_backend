import {
  QueryClient,
  QueryClientProvider,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import {
  BrowserRouter,
  Navigate,
  NavLink,
  Outlet,
  Route,
  Routes,
} from "react-router";

import { verUsuario } from "./api/auth";
import { useConfig } from "./api/config";
import { alCerrarSesion, cerrarSesion, obtenerToken } from "./api/sesion";
import { AvisosProvider, Confirmar } from "./components/Avisos";
import { Catalogos } from "./pages/Catalogos";
import { EditorReporte } from "./pages/EditorReporte";
import { EditorSemana } from "./pages/EditorSemana";
import { Login } from "./pages/Login";
import { Reportes } from "./pages/Reportes";

const queryClient = new QueryClient();

interface LayoutProps {
  almacenar: boolean;
  autenticacion: boolean;
  onSalir: () => void;
}

function PieSesion({ almacenar, autenticacion, onSalir }: LayoutProps) {
  const [confirmar, setConfirmar] = useState(false);
  const usuario = useQuery({
    queryKey: ["usuario"],
    queryFn: verUsuario,
    enabled: autenticacion,
  });
  if (!autenticacion)
    return (
      <p className="sidebar-pie">
        {almacenar ? "Uso local · 127.0.0.1" : "Los reportes no se guardan"}
      </p>
    );
  return (
    <div className="sidebar-pie sesion-pie">
      <small>{usuario.data?.correo ?? ""}</small>
      <button
        type="button"
        className="btn-secondary btn-sm"
        onClick={() => (almacenar ? onSalir() : setConfirmar(true))}
      >
        Cerrar sesión
      </button>
      <Confirmar
        abierto={confirmar}
        titulo="Cerrar sesión"
        mensaje="Si tienes una semana sin descargar, se perderá."
        textoConfirmar="Cerrar sesión"
        peligro
        onConfirmar={() => {
          setConfirmar(false);
          onSalir();
        }}
        onCancelar={() => setConfirmar(false)}
      />
    </div>
  );
}

function Layout(props: LayoutProps) {
  const { almacenar } = props;
  return (
    <div className="app-layout">
      <aside className="sidebar">
        <div className="marca">
          <span className="marca-logo" aria-hidden="true">
            SG
          </span>
          <div>
            <strong>Servicios Generales</strong>
            <small>Reporte semanal</small>
          </div>
        </div>
        <nav aria-label="Principal">
          <NavLink to="/" end>
            <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <path
                d="M7 3h7l5 5v13H7z M14 3v5h5 M10 13h6 M10 17h6"
                stroke="currentColor"
                strokeWidth="1.8"
                strokeLinejoin="round"
              />
            </svg>
            {almacenar ? "Reportes" : "Nuevo reporte"}
          </NavLink>
          <NavLink to="/catalogos">
            <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <path
                d="M4 6h16 M4 12h16 M4 18h10"
                stroke="currentColor"
                strokeWidth="1.8"
                strokeLinecap="round"
              />
            </svg>
            Catálogos
          </NavLink>
        </nav>
        <PieSesion {...props} />
      </aside>
      <main className="content">
        <Outlet />
      </main>
    </div>
  );
}

function useSesion(activa: boolean) {
  const queryClient = useQueryClient();
  const [autenticado, setAutenticado] = useState(() => Boolean(obtenerToken()));
  const [expirada, setExpirada] = useState(false);
  const saliendo = useRef(false);
  useEffect(
    () =>
      alCerrarSesion(() => {
        // Un 401 a mitad del trabajo no desmonta la pantalla: se pide entrar encima.
        if (saliendo.current) return;
        setExpirada(true);
      }),
    [],
  );
  return {
    autenticado: !activa || autenticado,
    expirada: activa && autenticado && expirada,
    entrar: () => {
      setAutenticado(true);
      setExpirada(false);
      void queryClient.invalidateQueries();
    },
    salir: () => {
      saliendo.current = true;
      cerrarSesion();
      saliendo.current = false;
      queryClient.clear();
      setExpirada(false);
      setAutenticado(false);
    },
  };
}

export function RutasAplicacion() {
  const config = useConfig();
  const sesion = useSesion(Boolean(config.data?.autenticacion));
  if (config.isPending) return <p className="empty">Cargando…</p>;
  if (config.isError)
    return (
      <section>
        <p role="alert" className="alert alert-error">
          {config.error.message}
        </p>
        <button type="button" onClick={() => void config.refetch()}>
          Reintentar
        </button>
      </section>
    );
  const { almacenar, autenticacion } = config.data;
  if (!sesion.autenticado) return <Login onEntrar={sesion.entrar} />;
  return (
    <>
      {sesion.expirada ? <Login expirada onEntrar={sesion.entrar} /> : null}
      <Routes>
        <Route
          element={
            <Layout
              almacenar={almacenar}
              autenticacion={autenticacion}
              onSalir={sesion.salir}
            />
          }
        >
          <Route
            index
            element={
              almacenar ? (
                <Reportes />
              ) : (
                <EditorSemana
                  maxFotosPorEspacio={config.data.max_fotos_por_espacio}
                />
              )
            }
          />
          <Route
            path="reportes/:id"
            element={
              almacenar ? <EditorReporte /> : <Navigate to="/" replace />
            }
          />
          <Route path="catalogos" element={<Catalogos />} />
        </Route>
      </Routes>
    </>
  );
}

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AvisosProvider>
        <BrowserRouter>
          <RutasAplicacion />
        </BrowserRouter>
      </AvisosProvider>
    </QueryClientProvider>
  );
}
