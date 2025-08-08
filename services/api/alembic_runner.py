"""
Helper to run Alembic migrations from Python code.

Usage (optional): python -m services.api.alembic_runner upgrade head
"""
from __future__ import annotations

import os
import sys
from alembic import command
from alembic.config import Config


def get_alembic_config() -> Config:
    here = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    ini_path = os.path.join(here, "alembic.ini")
    cfg = Config(ini_path)
    return cfg


def main(argv: list[str]) -> None:
    if not argv:
        print("Usage: alembic_runner.py [upgrade|downgrade|revision] ...")
        return

    cfg = get_alembic_config()
    cmd = argv[0]
    args = argv[1:]

    if cmd == "upgrade":
        rev = args[0] if args else "head"
        command.upgrade(cfg, rev)
    elif cmd == "downgrade":
        rev = args[0] if args else "-1"
        command.downgrade(cfg, rev)
    elif cmd == "revision":
        message = None
        autogenerate = False
        if "-m" in args:
            m_index = args.index("-m")
            if m_index + 1 < len(args):
                message = args[m_index + 1]
        if "--autogenerate" in args:
            autogenerate = True
        command.revision(cfg, message=message, autogenerate=autogenerate)
    else:
        print(f"Unknown command: {cmd}")


if __name__ == "__main__":
    main(sys.argv[1:])
