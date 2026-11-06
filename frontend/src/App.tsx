import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, NavLink, Outlet, Route, Routes } from "react-router";

import { Catalogos } from "./pages/Catalogos";
import { EditorReporte } from "./pages/EditorReporte";
import { Reportes } from "./pages/Reportes";

const queryClient = new QueryClient();

function Layout() {
  return (
    <div className="app-layout">
      <aside className="sidebar">
        <strong>Servicios Generales</strong>
        <nav aria-label="Principal">
          <NavLink to="/" end>
            Reportes
          </NavLink>
          <NavLink to="/catalogos">Catálogos</NavLink>
        </nav>
      </aside>
      <main className="content">
        <Outlet />
      </main>
    </div>
  );
}

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route index element={<Reportes />} />
            <Route path="reportes/:id" element={<EditorReporte />} />
            <Route path="catalogos" element={<Catalogos />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
