import { useQuery } from "@tanstack/react-query";

import { apiRequest } from "./client";

export interface Configuracion {
  almacenar: boolean;
  max_fotos_por_espacio: number;
}

export const verConfig = () => apiRequest<Configuracion>("/config");

export const useConfig = () =>
  useQuery({
    queryKey: ["config"],
    queryFn: verConfig,
    staleTime: Infinity,
  });
