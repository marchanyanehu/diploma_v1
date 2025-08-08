-- Initial database setup for Intelligent Web Data Aggregator
-- This script is run when the PostgreSQL container starts

-- Create database if it doesn't exist (already handled by POSTGRES_DB)
-- CREATE DATABASE IF NOT EXISTS diploma_db;

-- Set timezone to UTC
SET timezone = 'UTC';

-- Create extensions if needed
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Log initialization
SELECT 'Database initialization completed for diploma_db' as status;
