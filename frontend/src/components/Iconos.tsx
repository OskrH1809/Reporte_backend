interface Props {
  className?: string;
}

function Icono({ d, className }: Props & { d: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d={d} />
    </svg>
  );
}

export const IconoDescarga = (props: Props) => (
  <Icono {...props} d="M12 4v11 M7 10l5 5 5-5 M5 20h14" />
);
export const IconoPapelera = (props: Props) => (
  <Icono
    {...props}
    d="M4 7h16 M9 7V4h6v3 M6 7l1 13h10l1-13 M10 11v6 M14 11v6"
  />
);
export const IconoLapiz = (props: Props) => (
  <Icono {...props} d="M4 20h4L19 9l-4-4L4 16z M13 7l4 4" />
);
export const IconoMas = (props: Props) => (
  <Icono {...props} d="M12 5v14 M5 12h14" />
);
export const IconoBuscar = (props: Props) => (
  <Icono {...props} d="M11 18a7 7 0 1 0 0-14 7 7 0 0 0 0 14z M20 20l-4-4" />
);
