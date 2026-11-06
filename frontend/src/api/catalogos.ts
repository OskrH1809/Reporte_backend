import { apiRequest } from "./client";

export type TipoCatalogo =
  "colaboradores" | "herramientas" | "materiales" | "firmantes";
export interface Catalogo {
  id: number;
  nombre: string;
  orden: number | null;
  activo: boolean;
  unidad: string | null;
  tipo: "elabora" | "revisa" | null;
}
export interface CatalogoInput {
  nombre: string;
  unidad?: string;
  tipo?: "elabora" | "revisa";
}

export const listarCatalogo = (tipo: TipoCatalogo) =>
  apiRequest<Catalogo[]>(`/catalogos/${tipo}`);
export const crearCatalogo = (tipo: TipoCatalogo, input: CatalogoInput) =>
  apiRequest<Catalogo>(`/catalogos/${tipo}`, {
    method: "POST",
    body: JSON.stringify(input),
  });
export const editarCatalogo = (
  tipo: TipoCatalogo,
  id: number,
  input: CatalogoInput,
) =>
  apiRequest<Catalogo>(`/catalogos/${tipo}/${id}`, {
    method: "PATCH",
    body: JSON.stringify(input),
  });
export const desactivarCatalogo = (tipo: TipoCatalogo, id: number) =>
  apiRequest<void>(`/catalogos/${tipo}/${id}`, { method: "DELETE" });
