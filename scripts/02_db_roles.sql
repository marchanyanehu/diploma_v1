-- Auto-run roles script for Docker init
-- Passwords are read from environment variables set in docker-compose

\set ON_ERROR_STOP on

-- Create roles with passwords from env vars (set by Docker)
DO $$
DECLARE
    read_pwd TEXT := current_setting('app.read_pwd', true);
    write_pwd TEXT := current_setting('app.write_pwd', true);
    admin_pwd TEXT := current_setting('app.admin_pwd', true);
BEGIN
    -- Use defaults if env vars not set
    IF read_pwd IS NULL OR read_pwd = '' THEN read_pwd := 'change-me-strong-app-read'; END IF;
    IF write_pwd IS NULL OR write_pwd = '' THEN write_pwd := 'change-me-strong-app-write'; END IF;
    IF admin_pwd IS NULL OR admin_pwd = '' THEN admin_pwd := 'change-me-strong-app-admin'; END IF;

    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'app_read') THEN
        EXECUTE format('CREATE ROLE app_read LOGIN PASSWORD %L NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT', read_pwd);
    END IF;

    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'app_write') THEN
        EXECUTE format('CREATE ROLE app_write LOGIN PASSWORD %L NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT', write_pwd);
    END IF;

    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'app_admin') THEN
        EXECUTE format('CREATE ROLE app_admin LOGIN PASSWORD %L NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT', admin_pwd);
    END IF;
END $$;

GRANT CONNECT ON DATABASE diploma_db TO app_read, app_write, app_admin;
GRANT USAGE, CREATE ON SCHEMA public TO app_write, app_admin;
GRANT USAGE ON SCHEMA public TO app_read;

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

-- Sequences
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_read, app_write, app_admin;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO app_read, app_write, app_admin;

-- Timeouts
ALTER ROLE app_read SET statement_timeout = '30s';
ALTER ROLE app_write SET statement_timeout = '60s';
ALTER ROLE app_admin SET statement_timeout = '120s';
