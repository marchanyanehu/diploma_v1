**Auto Tests Diploma Project Requirements**

**Scope and Goals**

The goal of this document is to provide students with a clear overview of the expectations and evaluation criteria for diploma projects that include automated testing.

The document defines:

- Minimum requirements - mandatory criteria to obtain a passing grade (grade = 5).
- Maximum requirements - advanced criteria to achieve the highest grade (grade = 10).
- Major errors and shortcomings - critical issues resulting in penalties.

**Minimum Requirements (for a passing grade)**

- The project must include a structured and well-documented automated testing setup. The student must demonstrate the ability to create meaningful test cases and ensure that the application's core business logic is validated through automated tests.
- The project must achieve at least 70% code coverage, measured using appropriate tools (such as Istanbul/NYC for JavaScript, Coverlet for .NET, JaCoCo for Java, or equivalents). Coverage should be provided in the form of numerical metrics and, when possible, a coverage report or screenshot.
- A comprehensive suite of unit tests must be implemented to verify individual functions and methods in isolation. Tests should follow industry best practices, including the FIRST principles (Fast, Independent, Repeatable, Self-Validating, Timely). Each non-trivial function must have tests covering both common scenarios and edge cases.
- The project must also include integration tests that validate interactions between components. Examples include API endpoint tests, in-memory database testing, authentication/authorization checks, and validation of application configuration.
- If the application includes a frontend, the project must contain automated tests for the UI layer. These may include component tests (e.g., Jest + React Testing Library) and/or end-to-end tests using tools like Cypress, Playwright, or Selenium to verify key user flows.
- All automated tests must run in a continuous integration (CI) environment to ensure reproducibility on clean infrastructure. Test results must be visible in CI logs, showing that the full suite executes successfully.
- The report must describe the testing strategy, the types of tests implemented, the tools used, instructions for running tests locally, and any known gaps in coverage together with justification.
- Test files must follow a clear naming convention and directory structure (e.g., \*.test.js, tests/, or language-specific equivalents) to ensure maintainability.

**Maximum Requirements (for the highest grade)**

- The project must provide a highly comprehensive automated testing strategy that includes unit, integration, component, and end-to-end testing, demonstrating deep understanding of multi-layer test design.
- The test suite should cover all business-critical areas, including input validation, error handling, permission checks, and data processing. Advanced techniques such as mocking external services, test doubles, fixtures, and in-memory infrastructure should be used where appropriate.
- The project must extend testing to complex integration scenarios, such as multi-service interactions, database migrations, asynchronous workflows, or message queue operations. For distributed systems or microservices, component tests and full end-to-end scenarios must be included.
- Test quality must be enhanced through the use of additional tools or methodologies, such as property-based testing, mutation testing, snapshot testing, or contract tests for API stability.
- The test pipeline must run fully in CI/CD and include quality gates, such as minimum coverage thresholds, linting, and static analysis. Evidence of stable test execution (e.g., successful CI screenshots or badges) must be provided.
- The student must document the rationale behind test architecture decisions, demonstrate how automated tests improved code quality or helped identify defects, and provide recommendations for future enhancements to the test suite.
- Performance or load testing may be included to assess system behavior under stress.

**Major Errors and Shortcomings Affecting Evaluation**

| **Category** | **Example of issue** | **Penalty** |
| --- | --- | --- |
| Coverage | Test coverage below 70% | \-2 points |
| Test quality | Critical logic untested or missing edge cases | \-1 point |
| CI/CD | Tests not executed in CI or failing tests ignored | \-1 point |
| Documentation | Missing test strategy or unclear instructions | \-1 point |
| Stability | Presence of flaky or unstable tests | \-1 point |
| Architecture | No integration tests or missing checks for critical flows | \-1 point |
| Logic | Hardcoded outputs or tests that do not validate real logic | \-2 points |
| Code use | Inappropriate mocking or tests tightly coupled to implementation | \-1 point |