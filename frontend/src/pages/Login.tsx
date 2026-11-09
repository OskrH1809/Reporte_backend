import { useMutation } from "@tanstack/react-query";
import { type FormEvent, useEffect, useState } from "react";

import { iniciarSesion } from "../api/auth";
import { ApiError } from "../api/client";

const MS_AVISO_LENTO = 3000;

function mensajeLogin(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.code === "credenciales_invalidas")
      return "Correo o contraseña incorrectos.";
    if (error.code === "demasiados_intentos")
      return "Demasiados intentos. Espera 15 minutos.";
    if (error.status === 422) return "Escribe tu correo y contraseña.";
    return error.message;
  }
  return "No se pudo conectar con el servidor.";
}

interface Props {
  onEntrar: () => void;
  /** Sesión vencida mientras se trabajaba: se muestra encima sin perder la pantalla. */
  expirada?: boolean;
}

export function Login({ onEntrar, expirada = false }: Props) {
  const [correo, setCorreo] = useState("");
  const [contrasena, setContrasena] = useState("");
  const [lento, setLento] = useState(false);
  const entrar = useMutation({
    mutationFn: () => iniciarSesion(correo.trim(), contrasena),
    onSuccess: () => {
      setContrasena("");
      onEntrar();
    },
  });

  useEffect(() => {
    if (!entrar.isPending) return;
    // Render se duerme sin uso: la primera respuesta puede tardar casi un minuto.
    const temporizador = window.setTimeout(
      () => setLento(true),
      MS_AVISO_LENTO,
    );
    return () => {
      window.clearTimeout(temporizador);
      setLento(false);
    };
  }, [entrar.isPending]);

  function enviar(event: FormEvent) {
    event.preventDefault();
    if (!correo.trim() || !contrasena) return;
    entrar.mutate();
  }

  return (
    <section className={expirada ? "login login-modal" : "login"}>
      <form className="card login-card stack" onSubmit={enviar} noValidate>
        <header>
          <h1 className="card-title">
            {expirada ? "Tu sesión expiró" : "Servicios Generales"}
          </h1>
          <p className="muted">
            {expirada
              ? "Vuelve a iniciar sesión; lo que capturaste sigue aquí."
              : "Inicia sesión para continuar."}
          </p>
        </header>
        <label className="field">
          <span>Correo</span>
          <input
            type="email"
            autoComplete="username"
            value={correo}
            onChange={(event) => setCorreo(event.target.value)}
            required
          />
        </label>
        <label className="field">
          <span>Contraseña</span>
          <input
            type="password"
            autoComplete="current-password"
            value={contrasena}
            onChange={(event) => setContrasena(event.target.value)}
            required
          />
        </label>
        {entrar.isError ? (
          <p role="alert" className="alert alert-error">
            {mensajeLogin(entrar.error)}
          </p>
        ) : null}
        {lento ? (
          <p role="status" className="alert alert-warn">
            Conectando con el servidor… (puede tardar hasta un minuto)
          </p>
        ) : null}
        <button
          type="submit"
          disabled={entrar.isPending || !correo.trim() || !contrasena}
        >
          {entrar.isPending ? "Entrando…" : "Entrar"}
        </button>
      </form>
    </section>
  );
}
