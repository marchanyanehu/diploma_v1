#!/bin/bash
# sync_db_roles.sh - Synchronize database roles with configured passwords
# This script ensures the app_read, app_write, and app_admin roles exist
# with the correct passwords from environment variables.
# Safe to run multiple times (idempotent).

set -e

echo "Syncing database roles..."

# Use environment variables with defaults
READ_PWD="${DB_PASSWORD:-app_write_pwd}"
WRITE_PWD="${DB_PASSWORD:-app_write_pwd}"
ADMIN_PWD="${DB_PASSWORD:-app_write_pwd}"
DB_NAME_VAL="${DB_NAME:-diploma_db}"
DB_HOST_VAL="${DB_HOST:-postgres}"
PGUSER_VAL="${POSTGRES_USER:-postgres}"

# Wait for postgres to be ready
until PGPASSWORD="${POSTGRES_PASSWORD}" psql -h "${DB_HOST_VAL}" -U "${PGUSER_VAL}" -d "${DB_NAME_VAL}" -c '\q' 2>/dev/null; do
  echo "Waiting for postgres..."
  sleep 2
done

echo "PostgreSQL is ready. Syncing roles..."

# Run the role sync SQL (using shell variable expansion in heredoc)
PGPASSWORD="${POSTGRES_PASSWORD}" psql -h "${DB_HOST_VAL}" -U "${PGUSER_VAL}" -d "${DB_NAME_VAL}" <<EOSQL
DO \$\$
BEGIN
    -- Create or update app_read role
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'app_read') THEN
        EXECUTE format('CREATE ROLE app_read LOGIN PASSWORD %L NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT', '${READ_PWD}');
        RAISE NOTICE 'Created role app_read';
    ELSE
        EXECUTE format('ALTER ROLE app_read WITH PASSWORD %L', '${READ_PWD}');
        RAISE NOTICE 'Updated password for role app_read';
    END IF;

    -- Create or update app_write role
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'app_write') THEN
        EXECUTE format('CREATE ROLE app_write LOGIN PASSWORD %L NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT', '${WRITE_PWD}');
        RAISE NOTICE 'Created role app_write';
    ELSE
        EXECUTE format('ALTER ROLE app_write WITH PASSWORD %L', '${WRITE_PWD}');
        RAISE NOTICE 'Updated password for role app_write';
    END IF;

    -- Create or update app_admin role
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'app_admin') THEN
        EXECUTE format('CREATE ROLE app_admin LOGIN PASSWORD %L NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT', '${ADMIN_PWD}');
        RAISE NOTICE 'Created role app_admin';
    ELSE
        EXECUTE format('ALTER ROLE app_admin WITH PASSWORD %L', '${ADMIN_PWD}');
        RAISE NOTICE 'Updated password for role app_admin';
    END IF;
END \$\$;

-- Grant permissions (idempotent)
GRANT CONNECT ON DATABASE ${DB_NAME_VAL} TO app_read, app_write, app_admin;
GRANT USAGE, CREATE ON SCHEMA public TO app_write, app_admin;
GRANT USAGE ON SCHEMA public TO app_read;

-- Read-only permissions
GRANT SELECT ON ALL TABLES IN SCHEMA public TO app_read;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO app_read;

-- Read/Write permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_write;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO app_write;

-- Admin permissions
GRANT app_read TO app_write;
GRANT app_write TO app_admin;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO app_admin;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO app_admin;

-- Sequences
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_read, app_write, app_admin;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO app_read, app_write, app_admin;

-- Timeouts
ALTER ROLE app_read SET statement_timeout = '30s';
ALTER ROLE app_write SET statement_timeout = '60s';
ALTER ROLE app_admin SET statement_timeout = '120s';
EOSQL

echo "Database roles synchronized successfully!"
