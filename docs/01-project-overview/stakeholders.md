# Stakeholders & Users

- **End Users (Data Analysts, Operations Staff):** Non-technical professionals who need data from various websites for analysis. They will directly use the API (or UI) to create scraping jobs and consume results. They value ease of use, reliability, and timely results.
- **Business Sponsors (Product/Project Managers):** Decision-makers interested in business impact, such as faster time-to-insight and operational efficiency. They care about system delivering on promised goals (onboarding speed, maintenance reduction).
- **Technical Team (Backend Developers, Data Engineers, DevOps):** Responsible for building and maintaining the system. They design architecture (microservices, containers), ensure code quality (testing, CI/CD), and deploy infrastructure. Their concerns include scalability, reliability, and integration with external LLM APIs.
- **Security/Compliance Officers:** Oversight for legal/ethical use of data. They ensure that scraping adheres to site policies (robots.txt, GDPR), and the system itself is secure against vulnerabilities. They insist on features like authentication (JWT), rate limiting, input sanitization, and audit logging.
- **Administrator (Self-Service or Minimal UI):** Although the project is API-focused, if an admin or simple UI exists, that role could manage user accounts, view logs, and oversee scheduled jobs. (Currently, all management is via API endpoints.)

Each stakeholder contributes different perspectives: users define the functional needs (easy queries, scheduling), sponsors define success metrics (speed, cost savings), and technical/compliance teams define constraints (security, maintainability). Balancing these needs shaped the project design.
