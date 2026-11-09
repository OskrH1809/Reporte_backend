import { cerrarSesion, obtenerToken } from "./sesion";

// Vacía en local (nginx hace de proxy); en Vercel es la URL pública del backend.
const API_URL = (import.meta.env.VITE_API_URL ?? "").replace(/\/$/, "");

interface ErrorResponse {
  detail?: unknown;
  code?: unknown;
}

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly code: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function readError(response: Response): Promise<ErrorResponse> {
  try {
    return (await response.json()) as ErrorResponse;
  } catch {
    return {};
  }
}

export function urlApi(path: string): string {
  return `${API_URL}/api${path}`;
}

function conToken(headers: Headers): Headers {
  const token = obtenerToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  return headers;
}

async function apiError(response: Response): Promise<ApiError> {
  if (response.status === 401) cerrarSesion();
  const body = await readError(response);
  return new ApiError(
    typeof body.detail === "string" ? body.detail : "Error inesperado",
    response.status,
    typeof body.code === "string" ? body.code : "unexpected_error",
  );
}

export async function apiRequest<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  const headers = new Headers(init?.headers);
  if (typeof init?.body === "string")
    headers.set("Content-Type", "application/json");
  const response = await fetch(urlApi(path), {
    ...init,
    headers: conToken(headers),
  });
  if (!response.ok) {
    throw await apiError(response);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export async function apiDescarga(
  path: string,
  body: FormData,
): Promise<{ blob: Blob; nombre?: string }> {
  const response = await fetch(urlApi(path), {
    method: "POST",
    body,
    headers: conToken(new Headers()),
  });
  if (!response.ok) throw await apiError(response);
  const disposition = response.headers.get("Content-Disposition") ?? "";
  const coincidencia = /filename="?([^";]+)"?/i.exec(disposition);
  return {
    blob: await response.blob(),
    nombre: coincidencia?.[1],
  };
}
