"""Interfaz de línea de comandos: ``banxicolab --help``."""

from __future__ import annotations

import argparse
import sys

import pandas as pd

from . import __version__
from .alias import catalogo
from .cliente import Banxico
from .errores import BanxicoError
from .token import borrar_token, guardar_token, ruta_token


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="banxicolab", description="Series del SIE de Banco de México desde la terminal."
    )
    p.add_argument("--version", action="version", version=f"banxicolab {__version__}")
    sub = p.add_subparsers(dest="comando", required=True)

    t = sub.add_parser("token", help="guarda tu token de forma segura (no se muestra al escribir)")
    t.add_argument("--borrar", action="store_true", help="elimina el token guardado")

    c = sub.add_parser("catalogo", help="lista los alias de series disponibles")
    c.add_argument("tema", nargs="?", help="precios, tasas, tipo_de_cambio…")

    b = sub.add_parser("buscar", help="busca series por texto (no requiere token)")
    b.add_argument("texto")

    m = sub.add_parser("metadatos", help="título, periodicidad y cobertura de las series")
    m.add_argument("series", nargs="+")

    d = sub.add_parser("descargar", help="descarga series a CSV")
    d.add_argument("series", nargs="*", help="identificadores (SF43718) o alias (fix)")
    d.add_argument("--tema", help="en lugar de series: todo un tema del catálogo")
    d.add_argument(
        "--mensual", action="store_true", help="panel mensual con la regla de cada serie"
    )
    d.add_argument("--inicio", help="AAAA-MM-DD")
    d.add_argument("--fin", help="AAAA-MM-DD")
    d.add_argument("--incremento", choices=["mensual", "anual", "acumulado"])
    d.add_argument("-o", "--salida", help="archivo CSV; si se omite se imprime en pantalla")
    return p


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    pd.set_option("display.width", 200, "display.max_colwidth", 90, "display.max_rows", 200)
    try:
        if args.comando == "token":
            if args.borrar:
                print("Token eliminado." if borrar_token() else "No había token guardado.")
            else:
                guardar_token()
                print(f"Quedó en {ruta_token()} (solo legible por tu usuario).")
        elif args.comando == "catalogo":
            print(catalogo(args.tema).to_string())
        elif args.comando == "buscar":
            print(Banxico().buscar(args.texto, limite=None).to_string(index=False))
        elif args.comando == "metadatos":
            print(Banxico().metadatos(args.series).to_string())
        elif args.comando == "descargar":
            bmx, series = Banxico(), args.series or None
            if args.mensual:
                if args.incremento:
                    raise ValueError("--mensual e --incremento no se pueden combinar.")
                df = bmx.panel(series, args.inicio, args.fin, tema=args.tema)
            else:
                df = bmx.descargar(
                    series, args.inicio, args.fin, tema=args.tema, incremento=args.incremento
                )
            if args.salida:
                df.to_csv(args.salida, float_format="%.10g")
                print(f"{len(df):,} filas × {df.shape[1]} series → {args.salida}", file=sys.stderr)
            else:
                df.to_csv(sys.stdout, float_format="%.10g")
    except (BanxicoError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
