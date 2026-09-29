"""ProjectG desktop entry point."""

from projectg.bootstrap.startup import main

__all__ = ["main"]


if __name__ == "__main__":
    raise SystemExit(main())
