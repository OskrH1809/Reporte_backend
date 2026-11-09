const CLAVE = "sg_sesion";

interface SesionGuardada {
  token: string;
  expira_en: string;
}

type Oyente = () => void;
const oyentes = new Set<Oyente>();

// sessionStorage: la sesión muere al cerrar la pestaña y no se comparte entre pestañas.
function leer(): SesionGuardada | undefined {
  try {
    const crudo = sessionStorage.getItem(CLAVE);
    if (!crudo) return undefined;
    const sesion = JSON.parse(crudo) as Partial<SesionGuardada>;
    if (
      typeof sesion.token !== "string" ||
      typeof sesion.expira_en !== "string"
    )
      return undefined;
    return { token: sesion.token, expira_en: sesion.expira_en };
  } catch {
    return undefined;
  }
}

export function obtenerToken(ahora: Date = new Date()): string | undefined {
  const sesion = leer();
  if (!sesion) return undefined;
  const expira = Date.parse(sesion.expira_en);
  if (Number.isNaN(expira) || expira <= ahora.getTime()) return undefined;
  return sesion.token;
}

export function guardarToken(token: string, expiraEn: string): void {
  try {
    sessionStorage.setItem(
      CLAVE,
      JSON.stringify({ token, expira_en: expiraEn }),
    );
  } catch {
    // Sin almacenamiento disponible la sesión dura solo hasta recargar.
  }
}

export function cerrarSesion(): void {
  try {
    sessionStorage.removeItem(CLAVE);
  } catch {
    // Nada que limpiar.
  }
  for (const oyente of oyentes) oyente();
}

export function alCerrarSesion(oyente: Oyente): () => void {
  oyentes.add(oyente);
  return () => {
    oyentes.delete(oyente);
  };
}
