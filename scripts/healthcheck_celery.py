"""
Lightweight healthcheck for Celery workers.

Checks broker (Redis) connectivity and optionally Postgres connectivity.
Exit code 0 means healthy; non-zero means unhealthy.
"""

from __future__ import annotations

import os
import sys
from urllib.parse import urlparse

import redis

BROKER_URL = os.getenv("CELERY_BROKER_URL") or os.getenv("REDIS_URL") or "redis://redis:6379/0"


def check_redis() -> None:
    client = redis.from_url(BROKER_URL, socket_timeout=3)
    client.ping()


def check_postgres() -> None:
    import psycopg2  # imported lazily to keep overhead small

    host = os.getenv("DB_HOST")
    port = os.getenv("DB_PORT", "5432")
    dbname = os.getenv("DB_NAME")
    user = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")

    if not all([host, dbname, user, password]):
        return

    conn = psycopg2.connect(
        host=host,
        port=port,
        dbname=dbname,
        user=user,
        password=password,
        connect_timeout=3,
    )
    conn.close()


def main() -> int:
    try:
        check_redis()
        check_postgres()
        return 0
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write(f"healthcheck failed: {exc}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())

