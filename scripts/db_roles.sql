-- Role/bootstrap script for application roles (superuser preserved but unused by services)
-- Usage:
--   psql -h <host> -p <port> -U postgres -d diploma_db \
--     -v app_read_pwd='replace-with-strong' \
--     -v app_write_pwd='replace-with-strong' \
--     -v app_admin_pwd='replace-with-strong' \
--     -f scripts/db_roles.sql

\set ON_ERROR_STOP on

DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'app_read') THEN
        CREATE ROLE app_read LOGIN PASSWORD :'app_read_pwd' NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT;
    ELSE
        ALTER ROLE app_read WITH LOGIN PASSWORD :'app_read_pwd' NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT;
    END IF;

    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'app_write') THEN
        CREATE ROLE app_write LOGIN PASSWORD :'app_write_pwd' NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT;
    ELSE
        ALTER ROLE app_write WITH LOGIN PASSWORD :'app_write_pwd' NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT;
    END IF;

    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'app_admin') THEN
        CREATE ROLE app_admin LOGIN PASSWORD :'app_admin_pwd' NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT;
    ELSE
        ALTER ROLE app_admin WITH LOGIN PASSWORD :'app_admin_pwd' NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT;
    END IF;
END $$;

GRANT CONNECT ON DATABASE diploma_db TO app_read, app_write, app_admin;
GRANT USAGE ON SCHEMA public TO app_read, app_write, app_admin;

-- Read-only
GRANT SELECT ON ALL TABLES IN SCHEMA public TO app_read;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO app_read;

-- Read/Write (no DDL)
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_write;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO app_write;

-- Admin (no superuser)
GRANT app_read TO app_write;
GRANT app_write TO app_admin;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO app_admin;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO app_admin;

-- Keep sequences usable
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_read, app_write, app_admin;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO app_read, app_write, app_admin;

-- Optional: limit statement timeout for app roles (defensive)
ALTER ROLE app_read SET statement_timeout = '30s';
ALTER ROLE app_write SET statement_timeout = '60s';
ALTER ROLE app_admin SET statement_timeout = '120s';

