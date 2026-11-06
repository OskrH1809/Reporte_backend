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

export async function apiRequest<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  const headers = new Headers(init?.headers);
  if (typeof init?.body === "string")
    headers.set("Content-Type", "application/json");
  const response = await fetch(`/api${path}`, { ...init, headers });
  if (!response.ok) {
    const body = await readError(response);
    throw new ApiError(
      typeof body.detail === "string" ? body.detail : "Error inesperado",
      response.status,
      typeof body.code === "string" ? body.code : "unexpected_error",
    );
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}
