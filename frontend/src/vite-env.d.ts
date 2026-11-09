/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** URL pública del backend (Render). Vacía en local: nginx hace de proxy. */
  readonly VITE_API_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
