import {
  useMutation,
  useQueries,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { type FormEvent, useState } from "react";

import {
  type Catalogo,
  type CatalogoInput,
  crearCatalogo,
  desactivarCatalogo,
  editarCatalogo,
  listarCatalogo,
  type TipoCatalogo,
} from "../api/catalogos";
import { Confirmar, useAvisos } from "../components/Avisos";
import {
  IconoBuscar,
  IconoLapiz,
  IconoMas,
  IconoPapelera,
} from "../components/Iconos";

const textos: Record<TipoCatalogo, { titulo: string; singular: string }> = {
  colaboradores: { titulo: "Colaboradores", singular: "colaborador" },
  herramientas: { titulo: "Herramientas", singular: "herramienta" },
  materiales: { titulo: "Materiales", singular: "material" },
  firmantes: { titulo: "Firmantes", singular: "firmante" },
};
const pestanas = Object.keys(textos) as TipoCatalogo[];

const normalizar = (texto: string) =>
  texto
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .trim()
    .replace(/\s+/g, " ")
    .toLowerCase();

function duplicado(
  lista: Catalogo[],
  nombre: string,
  ignorarId?: number,
): Catalogo | undefined {
  const buscado = normalizar(nombre);
  if (!buscado) return undefined;
  return lista.find(
    (item) => item.id !== ignorarId && normalizar(item.nombre) === buscado,
  );
}

export function Catalogos() {
  const [tipo, setTipo] = useState<TipoCatalogo>("colaboradores");
  const [nombre, setNombre] = useState("");
  const [unidad, setUnidad] = useState("");
  const [tipoFirmante, setTipoFirmante] = useState<"elabora" | "revisa">(
    "elabora",
  );
  const [filtro, setFiltro] = useState("");
  const [editando, setEditando] = useState<Catalogo>();
  const [porDesactivar, setPorDesactivar] = useState<Catalogo>();
  const queryClient = useQueryClient();
  const { avisar } = useAvisos();
  const consultas = useQueries({
    queries: pestanas.map((clave) => ({
      queryKey: ["catalogos", clave],
      queryFn: () => listarCatalogo(clave),
    })),
  });
  const consulta = useQuery({
    queryKey: ["catalogos", tipo],
    queryFn: () => listarCatalogo(tipo),
  });
  const { titulo, singular } = textos[tipo];
  const lista = consulta.data ?? [];

  const invalidar = () =>
    queryClient.invalidateQueries({ queryKey: ["catalogos"] });
  const crear = useMutation({
    mutationFn: (valor: CatalogoInput) => crearCatalogo(tipo, valor),
    onSuccess: (creado) => {
      setNombre("");
      setUnidad("");
      avisar(`Se agregó «${creado.nombre}».`);
      return invalidar();
    },
    onError: (error) => avisar(error.message, "error"),
  });
  const editar = useMutation({
    mutationFn: ({ id, valor }: { id: number; valor: CatalogoInput }) =>
      editarCatalogo(tipo, id, valor),
    onSuccess: (editado) => {
      setEditando(undefined);
      avisar(`Se guardó «${editado.nombre}».`);
      return invalidar();
    },
    onError: (error) => avisar(error.message, "error"),
  });
  const desactivar = useMutation({
    mutationFn: (item: Catalogo) => desactivarCatalogo(tipo, item.id),
    onSuccess: (_, item) => {
      setPorDesactivar(undefined);
      avisar(`Se desactivó «${item.nombre}».`);
      return invalidar();
    },
    onError: (error) => {
      setPorDesactivar(undefined);
      avisar(error.message, "error");
    },
  });

  function valor(
    nombreActual: string,
    unidadActual: string,
    firmante: "elabora" | "revisa",
  ): CatalogoInput {
    return {
      nombre: nombreActual.trim().replace(/\s+/g, " "),
      ...(tipo === "materiales" ? { unidad: unidadActual.trim() } : {}),
      ...(tipo === "firmantes" ? { tipo: firmante } : {}),
    };
  }

  const repetidoNuevo = duplicado(lista, nombre);
  const faltaUnidad = tipo === "materiales" && !unidad.trim();
  const puedeAgregar =
    Boolean(nombre.trim()) &&
    !repetidoNuevo &&
    !faltaUnidad &&
    !crear.isPending;

  function agregar(event: FormEvent) {
    event.preventDefault();
    if (puedeAgregar) crear.mutate(valor(nombre, unidad, tipoFirmante));
  }

  const repetidoEdicion = editando
    ? duplicado(lista, editando.nombre, editando.id)
    : undefined;
  const edicionValida =
    editando !== undefined &&
    Boolean(editando.nombre.trim()) &&
    !repetidoEdicion &&
    (tipo !== "materiales" || Boolean(editando.unidad?.trim()));

  function guardarEdicion() {
    if (!editando || !edicionValida) return;
    editar.mutate({
      id: editando.id,
      valor: valor(
        editando.nombre,
        editando.unidad ?? "",
        editando.tipo ?? "elabora",
      ),
    });
  }

  const visibles = filtro.trim()
    ? lista.filter((item) =>
        normalizar(item.nombre).includes(normalizar(filtro)),
      )
    : lista;

  function cambiarTipo(nuevo: TipoCatalogo) {
    setTipo(nuevo);
    setEditando(undefined);
    setFiltro("");
    setNombre("");
    setUnidad("");
  }

  return (
    <section>
      <header className="page-header">
        <div>
          <h1>Catálogos</h1>
          <p className="subtitle">
            Las listas que aparecen en los selectores del reporte.
          </p>
        </div>
      </header>

      <div className="segmented" role="tablist" aria-label="Catálogos">
        {pestanas.map((clave, posicion) => (
          <button
            key={clave}
            type="button"
            role="tab"
            aria-selected={tipo === clave}
            onClick={() => cambiarTipo(clave)}
          >
            {textos[clave].titulo}
            <span className="badge badge-muted num">
              {consultas[posicion]?.data?.length ?? "…"}
            </span>
          </button>
        ))}
      </div>

      <div className="card catalogo-card">
        <form className="catalogo-form" onSubmit={agregar} noValidate>
          <label className="field catalogo-nombre">
            <span>Nombre</span>
            <input
              value={nombre}
              placeholder={`Nuevo ${singular}`}
              maxLength={150}
              aria-invalid={Boolean(repetidoNuevo)}
              aria-describedby={repetidoNuevo ? "nombre-repetido" : undefined}
              onChange={(event) => setNombre(event.target.value)}
            />
          </label>
          {tipo === "materiales" ? (
            <label className="field catalogo-unidad">
              <span>Unidad</span>
              <input
                value={unidad}
                placeholder="pza, m, kg…"
                maxLength={50}
                onChange={(event) => setUnidad(event.target.value)}
              />
            </label>
          ) : null}
          {tipo === "firmantes" ? (
            <label className="field">
              <span>Tipo</span>
              <select
                value={tipoFirmante}
                onChange={(event) =>
                  setTipoFirmante(event.target.value as "elabora" | "revisa")
                }
              >
                <option value="elabora">Elabora</option>
                <option value="revisa">Revisa</option>
              </select>
            </label>
          ) : null}
          <button type="submit" disabled={!puedeAgregar}>
            <IconoMas /> Agregar
          </button>
          <label className="buscador">
            <IconoBuscar />
            <input
              type="search"
              value={filtro}
              placeholder={`Buscar en ${titulo.toLowerCase()}`}
              aria-label="Buscar"
              onChange={(event) => setFiltro(event.target.value)}
            />
          </label>
        </form>
        {repetidoNuevo ? (
          <p id="nombre-repetido" className="field-error" role="alert">
            «{repetidoNuevo.nombre}» ya está en el catálogo.
          </p>
        ) : null}

        {consulta.error ? (
          <p role="alert" className="alert alert-error">
            {consulta.error.message}
          </p>
        ) : null}
        {consulta.isPending ? <p className="empty">Cargando…</p> : null}
        {consulta.data && visibles.length === 0 ? (
          <p className="empty">
            {filtro.trim()
              ? `Nada coincide con «${filtro.trim()}».`
              : `No hay ${titulo.toLowerCase()} activos.`}
          </p>
        ) : null}
        {visibles.length ? (
          <div className="tabla-contenedor tabla-plana">
            <table>
              <thead>
                <tr>
                  <th className="col-numero">#</th>
                  <th>Nombre</th>
                  {tipo === "materiales" ? <th>Unidad</th> : null}
                  {tipo === "firmantes" ? <th>Tipo</th> : null}
                  <th className="acciones">
                    <span className="visualmente-oculto">Acciones</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {visibles.map((item) => {
                  const enEdicion = editando?.id === item.id;
                  return (
                    <tr key={item.id}>
                      <td className="col-numero muted num">
                        {lista.indexOf(item) + 1}
                      </td>
                      <td>
                        {enEdicion ? (
                          <>
                            <input
                              className="input-tabla"
                              aria-label={`Nombre de ${item.nombre}`}
                              value={editando.nombre}
                              maxLength={150}
                              aria-invalid={Boolean(repetidoEdicion)}
                              autoFocus
                              onChange={(event) =>
                                setEditando({
                                  ...editando,
                                  nombre: event.target.value,
                                })
                              }
                              onKeyDown={(event) => {
                                if (event.key === "Enter") guardarEdicion();
                                if (event.key === "Escape")
                                  setEditando(undefined);
                              }}
                            />
                            {repetidoEdicion ? (
                              <p className="field-error" role="alert">
                                Ya existe «{repetidoEdicion.nombre}».
                              </p>
                            ) : null}
                          </>
                        ) : (
                          item.nombre
                        )}
                      </td>
                      {tipo === "materiales" ? (
                        <td>
                          {enEdicion ? (
                            <input
                              className="input-tabla input-corto"
                              aria-label={`Unidad de ${item.nombre}`}
                              value={editando.unidad ?? ""}
                              maxLength={50}
                              onChange={(event) =>
                                setEditando({
                                  ...editando,
                                  unidad: event.target.value,
                                })
                              }
                            />
                          ) : (
                            <span className="badge badge-muted">
                              {item.unidad}
                            </span>
                          )}
                        </td>
                      ) : null}
                      {tipo === "firmantes" ? (
                        <td>
                          {enEdicion ? (
                            <select
                              aria-label={`Tipo de ${item.nombre}`}
                              value={editando.tipo ?? "elabora"}
                              onChange={(event) =>
                                setEditando({
                                  ...editando,
                                  tipo: event.target.value as
                                    "elabora" | "revisa",
                                })
                              }
                            >
                              <option value="elabora">Elabora</option>
                              <option value="revisa">Revisa</option>
                            </select>
                          ) : (
                            <span className="badge">
                              {item.tipo === "revisa" ? "Revisa" : "Elabora"}
                            </span>
                          )}
                        </td>
                      ) : null}
                      <td className="acciones">
                        <div className="row-actions">
                          {enEdicion ? (
                            <>
                              <button
                                type="button"
                                className="btn-sm"
                                disabled={!edicionValida || editar.isPending}
                                onClick={guardarEdicion}
                              >
                                Guardar
                              </button>
                              <button
                                type="button"
                                className="btn-ghost btn-sm"
                                onClick={() => setEditando(undefined)}
                              >
                                Cancelar
                              </button>
                            </>
                          ) : (
                            <>
                              <button
                                type="button"
                                className="btn-ghost btn-icon"
                                aria-label={`Editar ${item.nombre}`}
                                title="Editar"
                                onClick={() => setEditando(item)}
                              >
                                <IconoLapiz />
                              </button>
                              <button
                                type="button"
                                className="btn-ghost btn-danger btn-icon"
                                aria-label={`Desactivar ${item.nombre}`}
                                title="Desactivar"
                                onClick={() => setPorDesactivar(item)}
                              >
                                <IconoPapelera />
                              </button>
                            </>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : null}
      </div>

      <Confirmar
        abierto={Boolean(porDesactivar)}
        titulo={`¿Desactivar «${porDesactivar?.nombre ?? ""}»?`}
        mensaje="Dejará de aparecer en los selectores. Los reportes ya capturados no cambian."
        textoConfirmar={desactivar.isPending ? "Desactivando…" : "Desactivar"}
        peligro
        onConfirmar={() => porDesactivar && desactivar.mutate(porDesactivar)}
        onCancelar={() => setPorDesactivar(undefined)}
      />
    </section>
  );
}
