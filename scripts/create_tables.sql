-- Create all tables required for the application
-- Run with: sudo docker exec diploma_postgres psql -U postgres -d diploma_db -f /tmp/create_tables.sql

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    email VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW(),
    is_active BOOLEAN DEFAULT true
);

CREATE TABLE IF NOT EXISTS scrape_tasks (
    id SERIAL PRIMARY KEY,
    task_id VARCHAR(100) UNIQUE NOT NULL,
    user_id INTEGER REFERENCES users(id),
    url TEXT NOT NULL,
    prompt TEXT NOT NULL,
    status VARCHAR(50) DEFAULT 'PENDING',
    result JSONB,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS scheduled_jobs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) NOT NULL,
    url TEXT NOT NULL,
    prompt TEXT NOT NULL,
    schedule_cron VARCHAR(100) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    last_run_at TIMESTAMP,
    next_run_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS regex_cache (
    id SERIAL PRIMARY KEY,
    url_pattern TEXT NOT NULL,
    field_name VARCHAR(100) NOT NULL,
    regex_pattern TEXT NOT NULL,
    extraction_type VARCHAR(50),
    hit_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    last_used_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(url_pattern, field_name)
);

-- Grant permissions
GRANT ALL ON ALL TABLES IN SCHEMA public TO app_write;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO app_write;

SELECT 'All tables created successfully!' as status;
