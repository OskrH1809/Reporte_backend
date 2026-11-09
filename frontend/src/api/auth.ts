import { apiRequest } from "./client";
import { guardarToken } from "./sesion";

export interface Usuario {
  id: number;
  correo: string;
}

interface LoginSalida {
  access_token: string;
  token_type: "bearer";
  expira_en: string;
}

export async function iniciarSesion(
  correo: string,
  contrasena: string,
): Promise<void> {
  const salida = await apiRequest<LoginSalida>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ correo, contrasena }),
  });
  guardarToken(salida.access_token, salida.expira_en);
}

export const verUsuario = () => apiRequest<Usuario>("/auth/yo");
