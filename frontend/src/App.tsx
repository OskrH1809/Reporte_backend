import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  BrowserRouter,
  Navigate,
  NavLink,
  Outlet,
  Route,
  Routes,
} from "react-router";

import { useConfig } from "./api/config";
import { AvisosProvider } from "./components/Avisos";
import { Catalogos } from "./pages/Catalogos";
import { EditorReporte } from "./pages/EditorReporte";
import { EditorSemana } from "./pages/EditorSemana";
import { Reportes } from "./pages/Reportes";

const queryClient = new QueryClient();

function Layout({ almacenar }: { almacenar: boolean }) {
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
        <p className="sidebar-pie">Uso local · 127.0.0.1</p>
      </aside>
      <main className="content">
        <Outlet />
      </main>
    </div>
  );
}

export function RutasAplicacion() {
  const config = useConfig();
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
  const almacenar = config.data.almacenar;
  return (
    <Routes>
      <Route element={<Layout almacenar={almacenar} />}>
        <Route index element={almacenar ? <Reportes /> : <EditorSemana />} />
        <Route
          path="reportes/:id"
          element={almacenar ? <EditorReporte /> : <Navigate to="/" replace />}
        />
        <Route path="catalogos" element={<Catalogos />} />
      </Route>
    </Routes>
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
