# Stakeholders & Users

## Target Audience

| Persona | Description | Key Needs |
|---------|-------------|-----------|
| **End Users** (Data Analysts, Operations) | Non-technical professionals who need data from various websites for analysis. | Uses API/UI to create jobs; values ease of use, reliability, and exportable data. |
| **Business Sponsors** (Product Managers) | Decision-makers interested in business impact and efficiency. | Faster time-to-insight, operational efficiency, system reliability. |
| **Technical Team** (Devs, DevOps) | Responsible for building, maintaining, and deploying the system. | Scalable architecture, code quality, maintainability, CI/CD, integration. |
| **Security/Compliance Officers** | Oversight for legal/ethical use of data and system security. | GDPR compliance, secure auth (JWT), rate limiting, audit logging. |
| **Administrator** | Manages user accounts, views logs, and oversees scheduled jobs. | User management tools, system visibility, logs access. |

## User Personas

### Persona 1: Sarah (Data Analyst)

| Attribute | Details |
|-----------|---------|
| **Role** | Senior Data Analyst at a Market Research Firm |
| **Age** | 29 |
| **Tech Savviness** | Medium (Comfortable with Excel/SQL, limited coding) |
| **Goals** | To quickly gather pricing data from competitor sites without writing scrapers manually. |
| **Frustrations** | Waiting for engineering to build custom scrapers; broken scripts when sites change. |
| **Scenario** | Sarah needs daily price updates from 5 e-commerce sites. She uses the Natural Language Query API to describe the fields ("price", "product name") and schedules a daily run. |

### Persona 2: Alex (Backend Developer)

| Attribute | Details |
|-----------|---------|
| **Role** | Backend Engineer supporting the analytics team |
| **Age** | 34 |
| **Tech Savviness** | High |
| **Goals** | To provide a robust infrastructure for data extraction that doesn't require constant maintenance. |
| **Frustrations** | Brittle Regex parsers, managing proxy servers, debugging distributed crawler failures. |
| **Scenario** | Alex deploys the containerized solution. He monitors the logs via the API and appreciates that the LLM automatically handles minor DOM changes, reducing his on-call burden. |

## Stakeholder Map

### High Influence / High Interest
- **Business Sponsors**: Direct ROI from the project.
- **End Users**: Daily reliance on the tool.

### High Influence / Low Interest
- **Security Officers**: Must sign off, but won't use it daily.

### Low Influence / High Interest
- **Technical Team**: Interested in the tech stack and maintenance, but implementation is driven by business needs.
