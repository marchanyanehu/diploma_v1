# Architecture Overview

## System Architecture

The Intelligent Web Data Aggregator API is a microservices-based architecture that provides intelligent web data aggregation capabilities. The system combines web scraping, natural language processing, and machine learning to extract structured data from web pages based on natural language prompts.

## High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Client Applications                       │
│  (Web Apps, Mobile Apps, CLI Tools, Integrations)           │
└──────────────────────────────┬──────────────────────────────┘
                               │ HTTP/REST API
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                    API Service (FastAPI)                    │
│  ├─ Authentication & Authorization (JWT)                    │
│  ├─ Request Validation & Rate Limiting                      │
│  ├─ Task Management & Status Tracking                       │
│  └─ Scheduling & User Management                            │
└──────────────────────────────┬──────────────────────────────┘
                               │ Celery Tasks
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                    Worker Services                          │
│  ┌────────────────────┐  ┌────────────────────┐            │
│  │  Headless Worker   │  │     AI Worker      │            │
│  │  (Web Scraping)    │  │ (LLM Processing)   │            │
│  └────────────────────┘  └────────────────────┘            │
└──────────────────────────────┬──────────────────────────────┘
                               │ Database & Cache
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                    Data Layer                               │
│  ┌────────────────────┐  ┌────────────────────┐            │
│  │   PostgreSQL       │  │      Redis         │            │
│  │  (Primary Store)   │  │ (Cache & Queue)    │            │
│  └────────────────────┘  └────────────────────┘            │
└───────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. API Service (FastAPI)

**Purpose**: Main entry point for client requests, handles authentication, validation, and task orchestration.

**Key Components**:
- **FastAPI Application**: Main web server with OpenAPI endpoints
- **Authentication Middleware**: JWT token validation and user session management
- **Rate Limiting**: Request throttling using Redis or in-memory storage
- **Input Sanitization**: Protection against prompt injection attacks
- **Error Handling**: Structured error responses and logging
- **CORS Management**: Cross-origin resource sharing configuration

**Location**: `services/api/`

### 2. Headless Worker

**Purpose**: Performs web scraping and content extraction using headless browsers.

**Key Responsibilities**:
- Fetch web page content
- Execute JavaScript for dynamic content
- Extract HTML/JSON/XML data
- Handle anti-bot measures
- Capture network requests

**Location**: `services/headless_worker/`

### 3. AI Worker

**Purpose**: Processes natural language prompts and generates extraction rules using LLMs.

**Key Responsibilities**:
- Intent extraction from user prompts
- Regex pattern generation
-
- Regex pattern generation
- Schema extraction and validation
- Caching of successful parsers
- LLM integration (DeepSeek, Gemini, OpenAI)

**Location**: `services/ai_worker/`

### 4. Data Layer

#### PostgreSQL Database
**Purpose**: Primary data storage with 3NF normalized schema.

**Key Tables**:
- `users`: User authentication and profiles
- `scraping_tasks`: Task metadata and status
- `parsers_cache`: Cached regex patterns and extraction rules
- `task_intents`: Normalized intent data
- `scheduled_jobs`: Scheduled job definitions
- `domains`: Domain lookup table (3NF normalization)
- `parser_samples`: Sample input/output data

#### Redis
**Purpose**: Caching, rate limiting, and Celery message broker.

**Key Uses**:
- Rate limit storage
- Celery task queue
- Session caching of successful parsers
- Session storage (optional)

### 5. Shared Infrastructure

**Location**: `shared/`

**Components**:
- `shared/config.py`: Centralized configuration management
- `shared/database/`: Database connection and models
- `shared/celery_app.py`: Celery configuration and task queue configuration
- `shared/correlation.py`: Request correlation ID utilities
- `shared/logging_utils.py`: Structured logging configuration

## Data Flow

### 1. Task Creation Flow

```
1. Client → API: POST /api/v1/process
   │   - URL and prompt
   │   - JWT token
   │
2. API Validation:
   │   - Authentication check
   │   - Rate limiting
   │   - Input sanitization
   │   - Schema validation
   │
3. Database: Create task record (PENDING)
   │
4. API: Return task_id (202 Accepted)
   │
4. Celery: Enqueue task to ai_queue
   │
5. AI Worker: Process task
   │   - Intent extraction
   │   - Check parser cache
   │   - Generate/validate regex
   │   - Enqueue task to fetching_queue
   │
6. Headless Worker: Fetch web content
   │   - Execute in headless browser
   │   - Extract content
   │   - Return to AI worker
   │
7. AI Worker: Apply regex extraction
   │   - Validate results
   │   - Validate results
   │   - Update task status
   │
8. Database: Update task (SUCCESS/FAILED)
   │
9. Client: Poll /api/v1/status/{task_id}
```

### 2. Authentication Flow

```
1. Client → API: POST /auth/register
   │   - Username, password, email
   │
2. API: Validate input
   │   - Check username uniqueness
   │   - Hash password (bcrypt)
   │   - Create user record
   │
3. Client: POST /auth/token
   │   - Username & password
   │
4. API: Verify credentials
   │   - Check password hash
   │   - Generate JWT token
   │   - Return access_token
   │
5. Client: Use token in Authorization header
   │   Authorization: Bearer <token>
```

### 3. Scheduled Job Flow

```
1. Client: POST /api/v1/jobs
   │   - URL, prompt, cron schedule
   │
2. API: Create scheduled job record
   │
3. Scheduler: Monitor cron schedules
   │
4. On schedule: Create task automatically
   │   - Same flow as manual task creation
   │
5. Results: Available via /api/v1/result
```

## Database Schema (3NF Normalized)

### Normalization Principles

1. **First Normal Form (1NF)**:
   - Atomic values, unique rows
2. **Second Normal Form (2NF)**: All non-key attributes depend on full primary key
3. **Third Normal Form (3NF)**: No transitive dependencies

### Key Normalization Decisions

1. **Domain Separation**: Extracted domain from URL to separate `domains table
2. **Intent Normalization**: Separated intent data to task_intents table
3. **Source Data Separation**: Large blobs moved to task_source_data
4. **Parser Samples**: Sample data separated to parser_samples table

### Schema Relationships

```
users
 ├── scraping_tasks (one-to-many
 ├── scheduled_jobs (one-to-many)
 │
scraping_tasks
 ├── task_intents (many-to-one)
 ├── parsers_cache (many-to-one)
 ├── task_source_data (one-to-one)
 │
parsers_cache
 ├── domains (many-to-one)
 ├── domains (many-to-one)
```

## Security Architecture

### 1. Authentication & Authorization

- **JWT Tokens**: Stateless authentication with configurable expiry
- **Password Hashing**: bcrypt with salt and work factor
- **Token Revocation**: Not implemented (t (stateless design)
- **User Roles**: Basic user model (future: admin roles)

### 2. Input Validation & Sanitization

- **Prompt Injection Protection**: Blocks common injection patterns
- **URL Validation**: Strict URL format validation
- **Schema Validation**: Pydantic models for all inputs
- **Rate Limiting**: Prevents abuse and DoS attacks

### 3. Data Protection

- **Database Encryption**: At-rest encryption (PostgreSQL)
- **Connection Security**: TLS for database connections
- **Environment Variables**: Sensitive data in .env files
- **Log Redaction**: PII data excluded from logs

## Scalability Considerations

### Horizontal Scaling

1. **API Service**: Stateless, can be scaled horizontally
2. **Celery Workers**: Multiple instances per queue type
3. **Database**: Read replicas for read-heavy workloads
4. **Redis**: Cluster mode for high availability

### Performance Optimizations

1. **Parser Caching**: Reuse successful regex patterns
2. **Intent Matching**: Hash-based intent matching
3. **Database Indexing**: Strategic indexes on frequently queried columns
4. **Connection Pooling**: SQLAlchemy connection pools
5. **Async Processing**: Non-blocking I/O operations

### Monitoring & Observability

1. **Health Checks**: `/health` and `/api/v1/health` endpoints
2. **Structured Logging**: JSON-formatted logs with correlation IDs
3. **Metrics**: Request timing, error rates, queue lengths
4. **Tracing**: Correlation ID propagation across services

## Deployment Options

### 1. Docker Compose (Development)

```yaml
version: '3.8'
services:
  api:
    build: ./services/api
    ports: ["8000:8000"]
    depends_on: [postgres, redis]
    environment:
      - DATABASE_URL=postgresql://postgres:password@db:5432/diploma_db
      - REDIS_URL=redis://redis:6379/0
  
  db:
    image: postgres:15
    environment:
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=diploma_db
  
  redis:
    image: redis:7-alpine
  
  celery-worker-ai:
    build: ./services/ai_worker
    command: celery -A shared.celery_app.celery_app worker -Q ai_queue --loglevelloglevel=info
    depends_on: [redis, db]
  
  celery-worker-headless:
    build: ./services/headless_worker
    command: celery -A shared.celery_app.celery_app worker -Q fetching_queue --loglevel=info
    command: celery -A shared.celery_app.celery_app worker -Q fetching_queue --loglevel=info
    depends_on: [redis, db]
```

### 2. Kubernetes (Production)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-deployment
spec:
  replicas: 3
  selector:
    matchLabels:
      app: api
  template:
    metadata:
      labels:
        app: api
    spec:
      containers:
      - name: api
      containers:
      - name: api
        image: diploma-api:latest
        ports:
        - containerPort: 8000
        envFrom:
        - configMapRef:
            name: api-config
        - secretRef:
            name: api-secrets
```

### 3. Server Error: secretRef:
            name: api-secrets
```

### 3. Serverless (Future)

- **API Gateway**: AWS API Gateway or Google Cloud Endpoints
- **Functions**: AWS Lambda or Google Cloud Functions
- **Database**: Managed PostgreSQL (RDS, Cloud SQL)
- **Queue**: Managed Redis (ElastiCache, Memorystore)

## Technology Choices

### Why FastAPI?

- **Performance**: Built on Starlette and Pydantic, very fast
- **Async Support**: Native async/await support
- **Type Hints**: Full Python type hint support
- **Auto Docs**: Automatic Docs**: Automatic OpenAPI documentation generation
- **Dependency Injection**: Clean dependency management

### Why Celery?

- **Distributed Task Queue**: Reliable task execution
- **Redis Backend**: Fast and reliable message broker
- **Retry Mechanisms**: Built-in retry with exponential backoff
- **Monitoring**: Monitoring and management tools
- **Python Integration**: Native Python support

### Why PostgreSQL?

- **ACID Compliance**: Reliable transactions
- **JSON Support**: Native JSON/JSONB data types
- **Full-Text Search**: Advanced text search capabilities
- **Extensions**: Rich ecosystem of Extensions**: Rich ecosystem of extensions

## Future Architecture Considerations

### 1. Microservices Evolution

- **Service Mesh**: Istio or Linkerd for service-to-service communication
- **API Gateway**: Kong or Ambassador for API management
- **Event Sourcing**: Kafka or RabbitMQ for event-driven architecture
- **Service Discovery**: Consul or etcd for dynamic service discovery

### 2. Machine Learning Pipeline

- **Model Training**: Separate training pipeline for parser improvement
- **A/B Testing**: Canary deployments for new parser versions
- **Feedback Loop**: User feedback incorporation into model training
- **Model Versioning**: Automated model retraining and deployment

### 3. Multi-Tenancy

- **Data Isolation**: Schema-per-tenant or row-level security
- **Billing Integration**: Usage tracking and billing
- **Customization**: Tenant-specific configurations
- **Compliance**: GDPR, HIPAA, etc. **Compliance**: GDPR, CCPA, and other regulations

## Conclusion

The Intelligent Web Data Aggregator API is designed as a scalable, maintainable system that balances performance with developer experience. The microservices architecture allows independent scaling of components, while shared infrastructure ensures consistency across services.

Key architectural principles of the system is built with extensibility in mind, allowing for future enhancements like additional LLM providers, new data sources, and advanced analytics capabilities.