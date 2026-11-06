import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import {
  type Catalogo,
  type CatalogoInput,
  crearCatalogo,
  desactivarCatalogo,
  editarCatalogo,
  listarCatalogo,
  type TipoCatalogo,
} from "../api/catalogos";

const pestanas: Array<[TipoCatalogo, string]> = [
  ["colaboradores", "Colaboradores"],
  ["herramientas", "Herramientas"],
  ["materiales", "Materiales"],
  ["firmantes", "Firmantes"],
];

export function Catalogos() {
  const [tipo, setTipo] = useState<TipoCatalogo>("colaboradores");
  const [nombre, setNombre] = useState("");
  const [unidad, setUnidad] = useState("");
  const [tipoFirmante, setTipoFirmante] = useState<"elabora" | "revisa">(
    "elabora",
  );
  const [editando, setEditando] = useState<Catalogo>();
  const queryClient = useQueryClient();
  const consulta = useQuery({
    queryKey: ["catalogos", tipo],
    queryFn: () => listarCatalogo(tipo),
  });
  const invalidar = () =>
    queryClient.invalidateQueries({ queryKey: ["catalogos"] });
  const crear = useMutation({
    mutationFn: (valor: CatalogoInput) => crearCatalogo(tipo, valor),
    onSuccess: invalidar,
  });
  const editar = useMutation({
    mutationFn: ({ id, valor }: { id: number; valor: CatalogoInput }) =>
      editarCatalogo(tipo, id, valor),
    onSuccess: () => {
      setEditando(undefined);
      return invalidar();
    },
  });
  const eliminar = useMutation({
    mutationFn: (id: number) => desactivarCatalogo(tipo, id),
    onSuccess: invalidar,
  });

  function valor(nombreActual: string, unidadActual = unidad): CatalogoInput {
    return {
      nombre: nombreActual,
      ...(tipo === "materiales" ? { unidad: unidadActual } : {}),
      ...(tipo === "firmantes" ? { tipo: tipoFirmante } : {}),
    };
  }

  function agregar(event: React.FormEvent) {
    event.preventDefault();
    crear.mutate(valor(nombre), {
      onSuccess: () => {
        setNombre("");
        setUnidad("");
      },
    });
  }

  const error = consulta.error ?? crear.error ?? editar.error ?? eliminar.error;
  return (
    <section>
      <h1>Catálogos</h1>
      <div className="tabs" role="tablist" aria-label="Catálogos">
        {pestanas.map(([clave, etiqueta]) => (
          <button
            key={clave}
            type="button"
            role="tab"
            aria-selected={tipo === clave}
            onClick={() => setTipo(clave)}
          >
            {etiqueta}
          </button>
        ))}
      </div>
      <form className="inline-form" onSubmit={agregar}>
        <label>
          Nombre
          <input
            value={nombre}
            onChange={(event) => setNombre(event.target.value)}
            required
          />
        </label>
        {tipo === "materiales" ? (
          <label>
            Unidad
            <input
              value={unidad}
              onChange={(event) => setUnidad(event.target.value)}
              required
            />
          </label>
        ) : null}
        {tipo === "firmantes" ? (
          <label>
            Tipo
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
        <button type="submit">Agregar</button>
      </form>
      {error ? (
        <p role="alert" className="error-message">
          {error.message}
        </p>
      ) : null}
      {consulta.isPending ? <p>Cargando…</p> : null}
      {consulta.data ? (
        <table>
          <thead>
            <tr>
              <th>Nombre</th>
              {tipo === "materiales" ? <th>Unidad</th> : null}
              {tipo === "firmantes" ? <th>Tipo</th> : null}
              <th>Acciones</th>
            </tr>
          </thead>
          <tbody>
            {consulta.data.map((item) => (
              <tr key={item.id}>
                <td>
                  {editando?.id === item.id ? (
                    <input
                      aria-label={`Nombre de ${item.nombre}`}
                      value={editando.nombre}
                      onChange={(event) =>
                        setEditando({ ...editando, nombre: event.target.value })
                      }
                    />
                  ) : (
                    item.nombre
                  )}
                </td>
                {tipo === "materiales" ? (
                  <td>
                    {editando?.id === item.id ? (
                      <input
                        aria-label={`Unidad de ${item.nombre}`}
                        value={editando.unidad ?? ""}
                        onChange={(event) =>
                          setEditando({
                            ...editando,
                            unidad: event.target.value,
                          })
                        }
                      />
                    ) : (
                      item.unidad
                    )}
                  </td>
                ) : null}
                {tipo === "firmantes" ? <td>{item.tipo}</td> : null}
                <td className="row-actions">
                  {editando?.id === item.id ? (
                    <button
                      type="button"
                      onClick={() =>
                        editar.mutate({
                          id: item.id,
                          valor: valor(editando.nombre, editando.unidad ?? ""),
                        })
                      }
                    >
                      Guardar
                    </button>
                  ) : (
                    <button type="button" onClick={() => setEditando(item)}>
                      Editar
                    </button>
                  )}
                  <button
                    type="button"
                    onClick={() => eliminar.mutate(item.id)}
                  >
                    Desactivar
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : null}
    </section>
  );
}
