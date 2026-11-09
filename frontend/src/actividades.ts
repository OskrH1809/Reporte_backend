import { LETRAS, type Actividad, type Foto, type Letra } from "./api/reportes";

export function armarActividades(
  guardadas: Actividad[],
  fotos: Pick<Foto, "espacio">[] = [],
): Actividad[] {
  const porLetra = new Map(
    guardadas.map((actividad) => [actividad.letra, actividad]),
  );
  const indiceMasAlto = Math.max(
    1,
    ...guardadas.map((actividad) => LETRAS.indexOf(actividad.letra)),
    ...fotos.map((foto) =>
      foto.espacio === "AD" ? -1 : LETRAS.indexOf(foto.espacio),
    ),
  );
  return LETRAS.slice(0, indiceMasAlto + 1).map(
    (letra) =>
      porLetra.get(letra) ?? {
        letra,
        descripcion: "",
        asignaciones: [],
      },
  );
}

export function siguienteLetra(actividades: Actividad[]): Letra | undefined {
  const indiceMasAlto = Math.max(
    -1,
    ...actividades.map((actividad) => LETRAS.indexOf(actividad.letra)),
  );
  return LETRAS[indiceMasAlto + 1];
}

export function puedeQuitar(
  actividad: Actividad,
  esUltima: boolean,
  fotos: Pick<Foto, "espacio">[],
): boolean {
  return (
    LETRAS.indexOf(actividad.letra) > 1 &&
    esUltima &&
    actividad.descripcion.trim() === "" &&
    actividad.asignaciones.length === 0 &&
    !fotos.some((foto) => foto.espacio === actividad.letra)
  );
}

export function espaciosFotos(
  actividades: Actividad[],
  maximo = 4,
): [Letra | "AD", string, number][] {
  return [
    ...actividades.map((actividad): [Letra, string, number] => [
      actividad.letra,
      `Actividad ${actividad.letra}`,
      maximo,
    ]),
    ["AD", "Antes y después", maximo],
  ];
}
