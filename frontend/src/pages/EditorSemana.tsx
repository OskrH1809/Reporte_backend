import { useQuery } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";

import { listarCatalogo } from "../api/catalogos";
import type { DiaInput, Letra } from "../api/reportes";
import { Confirmar, useAvisos } from "../components/Avisos";
import { BotonDescarga } from "../components/BotonDescarga";
import { FormularioDia, SelectorFirmas } from "../components/FormularioDia";
import {
  armarFormData,
  comprimirFoto,
  crearSemana,
  semanaISO,
  type FotoLocal,
} from "../semana";
import "../editor.css";

const nombres = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"];
let siguienteFoto = 0;

export function EditorSemana() {
  const actual = semanaISO(new Date());
  const [semana, setSemana] = useState(() =>
    crearSemana(actual.anio, actual.semana),
  );
  const [anioNuevo, setAnioNuevo] = useState(actual.anio);
  const [semanaNueva, setSemanaNueva] = useState(actual.semana);
  const [diaActual, setDiaActual] = useState(0);
  const [modificado, setModificado] = useState(false);
  const [confirmarNueva, setConfirmarNueva] = useState(false);
  const [hayErrores, setHayErrores] = useState(false);
  const [subiendoEspacio, setSubiendoEspacio] = useState<Letra | "AD">();
  const [actividadesAbiertas, setActividadesAbiertas] = useState(
    new Set<Letra>(),
  );
  const fotosActuales = useRef<FotoLocal[]>([]);
  const { avisar } = useAvisos();
  const colaboradores = useQuery({
    queryKey: ["catalogos", "colaboradores"],
    queryFn: () => listarCatalogo("colaboradores"),
  });
  const herramientas = useQuery({
    queryKey: ["catalogos", "herramientas"],
    queryFn: () => listarCatalogo("herramientas"),
  });
  const materiales = useQuery({
    queryKey: ["catalogos", "materiales"],
    queryFn: () => listarCatalogo("materiales"),
  });
  const firmantes = useQuery({
    queryKey: ["catalogos", "firmantes"],
    queryFn: () => listarCatalogo("firmantes"),
  });

  useEffect(() => {
    fotosActuales.current = semana.dias.flatMap((dia) => dia.fotos);
  }, [semana.dias]);
  useEffect(
    () => () => {
      for (const foto of fotosActuales.current) URL.revokeObjectURL(foto.url);
    },
    [],
  );
  useEffect(() => {
    if (!modificado) return;
    const prevenirSalida = (event: BeforeUnloadEvent) => event.preventDefault();
    window.addEventListener("beforeunload", prevenirSalida);
    return () => window.removeEventListener("beforeunload", prevenirSalida);
  }, [modificado]);

  const dia = semana.dias[diaActual]!;
  function cambiarDia(valor: DiaInput) {
    setSemana((actual) => ({
      ...actual,
      dias: actual.dias.map((item, indice) =>
        indice === diaActual ? { ...item, ...valor } : item,
      ),
    }));
    setModificado(true);
  }
  function iniciarSemana() {
    for (const foto of fotosActuales.current) URL.revokeObjectURL(foto.url);
    setSemana(crearSemana(anioNuevo, semanaNueva));
    setDiaActual(0);
    setActividadesAbiertas(new Set());
    setModificado(false);
    setConfirmarNueva(false);
  }
  async function agregarFotos(espacio: Letra | "AD", archivos: File[]) {
    const disponibles =
      4 - dia.fotos.filter((foto) => foto.espacio === espacio).length;
    const seleccionados = archivos.slice(0, disponibles);
    if (archivos.length > disponibles)
      avisar(
        `Solo se agregaron ${seleccionados.length} foto(s); el máximo es 4.`,
        "info",
      );
    setSubiendoEspacio(espacio);
    const nuevas: FotoLocal[] = [];
    for (const archivo of seleccionados) {
      const comprimida = await comprimirFoto(archivo);
      nuevas.push({
        id: `foto-local-${++siguienteFoto}`,
        espacio,
        archivo: comprimida,
        url: URL.createObjectURL(comprimida),
        nombre_original: archivo.name,
      });
    }
    setSemana((actual) => ({
      ...actual,
      dias: actual.dias.map((item, indice) =>
        indice === diaActual
          ? { ...item, fotos: [...item.fotos, ...nuevas] }
          : item,
      ),
    }));
    if (nuevas.length) setModificado(true);
    setSubiendoEspacio(undefined);
  }
  function eliminarFoto(id: string | number) {
    const foto = dia.fotos.find((item) => item.id === id);
    if (!foto) return;
    URL.revokeObjectURL(foto.url);
    setSemana((actual) => ({
      ...actual,
      dias: actual.dias.map((item, indice) =>
        indice === diaActual
          ? {
              ...item,
              fotos: item.fotos.filter((entrada) => entrada.id !== id),
            }
          : item,
      ),
    }));
    setModificado(true);
  }

  return (
    <section className="editor stack">
      <header className="page-header">
        <div>
          <h1>Nuevo reporte semanal</h1>
          <p className="subtitle">
            Este reporte no se guarda: descarga los archivos antes de cerrar la
            pestaña.
          </p>
        </div>
        <div className="cluster">
          <BotonDescarga
            tipo="formato"
            etiqueta="Formato actual"
            obtenerDatos={() => armarFormData(semana)}
            deshabilitado={hayErrores}
          />
          <BotonDescarga
            tipo="mejorado"
            etiqueta="Excel mejorado"
            obtenerDatos={() => armarFormData(semana)}
            deshabilitado={hayErrores}
          />
          <BotonDescarga
            tipo="pdf"
            etiqueta="PDF"
            obtenerDatos={() => armarFormData(semana)}
            deshabilitado={hayErrores}
          />
        </div>
      </header>

      <section className="card nuevo-reporte">
        <h2 className="card-title">Semana</h2>
        <div className="nuevo-reporte-campos">
          <label className="field">
            <span>Año</span>
            <input
              type="number"
              min={2000}
              max={2100}
              value={anioNuevo}
              onChange={(event) => setAnioNuevo(event.target.valueAsNumber)}
            />
          </label>
          <label className="field">
            <span>Semana</span>
            <input
              type="number"
              min={1}
              max={53}
              value={semanaNueva}
              onChange={(event) => setSemanaNueva(event.target.valueAsNumber)}
            />
          </label>
        </div>
        <button
          type="button"
          onClick={() =>
            modificado ? setConfirmarNueva(true) : iniciarSemana()
          }
        >
          Nueva semana
        </button>
      </section>

      <SelectorFirmas
        firmantes={firmantes.data ?? []}
        elaboradoPorId={semana.elaborado_por_id}
        revisadoPorId={semana.revisado_por_id}
        onChange={(campo, valor) => {
          setSemana((actual) => ({ ...actual, [campo]: valor }));
          setModificado(true);
        }}
      />

      <div className="segmented dias-tabs" role="tablist">
        {nombres.map((nombre, indice) => (
          <button
            key={nombre}
            type="button"
            role="tab"
            aria-selected={diaActual === indice}
            onClick={() => setDiaActual(indice)}
          >
            <span className="dia-completo">{nombre}</span>
            <small>
              {semana.dias[indice]!.fecha.slice(5).replace("-", "/")}
            </small>
          </button>
        ))}
      </div>

      <FormularioDia
        dia={dia}
        onChange={cambiarDia}
        jornada={diaActual === 5 ? 5 : 8}
        catalogos={{
          colaboradores: colaboradores.data ?? [],
          herramientas: herramientas.data ?? [],
          materiales: materiales.data ?? [],
        }}
        fotos={dia.fotos}
        subiendoEspacio={subiendoEspacio}
        onSubirFotos={(espacio, archivos) =>
          void agregarFotos(espacio, archivos)
        }
        onEliminarFoto={eliminarFoto}
        actividadesAbiertas={actividadesAbiertas}
        setActividadesAbiertas={setActividadesAbiertas}
        onExcesoFotos={(agregadas, limite) =>
          avisar(
            `Solo se agregaron ${agregadas} foto(s); el máximo es ${limite}.`,
            "info",
          )
        }
        onVerificacion={setHayErrores}
      />

      <Confirmar
        abierto={confirmarNueva}
        titulo="Nueva semana"
        mensaje="Hay datos sin descargar. ¿Crear una semana nueva?"
        textoConfirmar="Crear nueva"
        onConfirmar={iniciarSemana}
        onCancelar={() => setConfirmarNueva(false)}
      />
    </section>
  );
}
