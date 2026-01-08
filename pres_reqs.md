

---

# Diploma Project Presentation Requirements

## Format

| Parameter        | Requirement                    |
| ---------------- | ------------------------------ |
| **File format**  | `.pptx` (PowerPoint) or `.pdf` |
| **Slides**       | 18–24 slides                   |
| **Language**     | English                        |
| **Aspect ratio** | 16:9                           |

---

## Presentation Structure

### 1. Title Slide (1 slide)

**Must include:**

* Project name
* Student name, group
* Supervisor name
* Date

---

### 2. Problem (1–2 slides)

**Must answer:**

* What problem are you solving?
* Who has this problem? (target audience)
* Why is it important? (consequences of not solving)

**Format:**
Use pain points, statistics, or user quotes if available.

---

### 3. Solution (1–2 slides)

**Must include:**

* How does your product solve the problem?
* Key features (3–5 main capabilities)
* What makes it different from alternatives?

**Format:**
Brief, visual. No walls of text.

---

### 4. Demo Screenshots (2–3 slides)

**Must show:**

* Main screens of the application
* Key user flow (e.g., registration → main action → result)
* UI states (empty, filled, error) — optional

**Format:**
Actual screenshots, not mockups. Annotate if needed. GIFs welcome.

---

### 5. Architecture (1–2 slides)

**Must include:**

* High-level architecture diagram (components and their connections)
* Technology stack (brief list or visual)
* Database schema (simplified) — optional

**Format:**
Diagram required. Keep it readable (not too detailed).

---

### 6. Evaluation Criteria (7 slides)

**One slide per criterion. Each slide must include:**

| Element                  | Description                                                    |
| ------------------------ | -------------------------------------------------------------- |
| **Criterion name**       | Clear title                                                    |
| **Why this approach**    | 1–2 sentences on decision rationale                            |
| **What was implemented** | Key features/components (3–5 bullet points)                    |
| **Technologies used**    | Specific tools, libraries, frameworks                          |
| **Diagram / Schema**     | Visual representation (architecture, flow, schema, screenshot) |

**Example slide content:**

```
Criterion: Database (OLTP)

WHY:
Needed relational DB for transactional data with complex relations

WHAT:
- PostgreSQL with 12 tables, 3NF normalized
- Migrations via Flyway
- Role-based access (app_read, app_write, admin)
- Indexes on frequently queried columns

TECH:
PostgreSQL 15, Flyway, pgAdmin

[ER Diagram]
```

**Visual required:**
Each criterion slide must have at least one diagram, schema, screenshot, or code snippet.

---

### 7. Challenges & Solutions (1 slide)

**Must include:**

* 2–3 significant technical challenges faced
* How each was solved
* What was learned

**Format:**
Table or bullet points with **Problem → Solution** structure.

---

### 8. Results (1 slide)

**Must include:**

* Checklist of completed features (✅ / ❌)
* What’s in the current version vs. future backlog
* Link to deployed application
* Key metrics (test coverage, performance, etc.) — if available

---

### 9. Q&A (1 slide)

**Must include:**

* Production URL
* Repository link
* API documentation link (Swagger)
* Design link (Figma) — if applicable
* QR code to production — optional

---

## Slide Count Summary

| Section          | Slides    |
| ---------------- | --------- |
| Title            | 1         |
| Problem          | 1–2       |
| Solution         | 1–2       |
| Demo             | 2–3       |
| Architecture     | 1–2       |
| Criteria (7 × 1) | 7         |
| Challenges       | 1         |
| Results          | 1         |
| Q&A              | 1         |
| **Total**        | **18–24** |

---

## Quality Requirements

### Content

* All text in English
* No placeholder text (`{description}`, `Lorem ipsum`)
* All links are working
* Screenshots are from the actual application (not mockups)
* Diagrams are readable and labeled

### Design

* Consistent visual style throughout
* Readable font size (minimum **18pt** body text)
* Sufficient contrast (text vs. background)
* No walls of text (max **6–7 bullet points per slide**)
* Images and diagrams are high quality (not blurry)

### Technical

* File opens without errors
* No missing fonts or broken elements
* File size reasonable (**< 50 MB**)

---

## Common Mistakes to Avoid

### ❌ Don’t

* Read slides word-by-word
* Put entire paragraphs on slides
* Use tiny fonts
* Show raw code (20+ lines)
* Skip the “why”
* Use generic diagrams from the internet
* Leave empty sections

### ✅ Do

* Use slides as visual support
* Use short bullet points (5–7 words)
* Minimum **18pt body**, **24pt+ headers**
* Show key snippets (5–10 lines) or pseudocode
* Always explain your decisions
* Create diagrams specific to your project
* Mark **N/A** with explanation if something doesn’t apply

---

## File Naming

```
[LastName]_Presentation.pptx
```

**Example:**

```
Ivanov_Presentation.pptx
```

---

