# Criterion: Deployment

## Description
The application is deployed to a remote cloud environment to demonstrate real-world viability and accessibility.

## Infrastructure
- **Provider**: Google Cloud Platform (GCP).
- **Service**: Compute Engine (VM Instance).
- **OS**: Ubuntu LTS.
- **Orchestration**: Docker Compose V2.

## Deployment Strategy
- **Manual Deployment**: Code is pulled from the repository and deployed via `docker compose up --build`.
- **Infrastructure Code**: `docker-compose.yml` defines the entire stack (API, DB, Redis, Workers, Frontend wrapper).
- **Network**: All services run in an isolated Docker bridge network, with only ports 80 (HTTP) and potentially 443 (HTTPS) exposed to the public internet.

## CI/CD Status
- **Manual Workflows**: Automatic pipelines (GitHub Actions) are currently disabled to allow for granular control during the active development/diploma defense phase. Deployment is triggered manually via SSH.
