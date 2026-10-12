"""Permite ``python -m banxicolab`` cuando el comando no está en el PATH."""

from .cli import main

raise SystemExit(main())
