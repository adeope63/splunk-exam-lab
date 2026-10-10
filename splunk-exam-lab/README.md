# Splunk Exam Lab

Personal, local-only SPLK-1002 practice platform. React + TypeScript + Vite + Tailwind CSS, FastAPI, SQLite + SQLAlchemy + Alembic, Recharts and Lucide icons. No registration, hosted authentication, billing, external database, or telemetry.

## Start

Install Python 3.10+ (also tested here with 3.9), Node.js 20.19+ or 22+, and pnpm (`npm install -g pnpm`). The first installation needs internet access to download dependencies. Study sessions themselves work locally without internet; documentation links open Splunk's website.

**Linux/macOS:** run `./start.sh` from this directory.

**Windows:** double-click `start.bat`, or run it in Command Prompt. Close both the backend window and frontend process to stop.

Open **http://127.0.0.1:5173**. The backend defaults to **127.0.0.1:8000**. API documentation is at http://127.0.0.1:8000/docs. Do not run multiple backend workers against this personal database. Avoid running multiple exam tabs while answering the same session.

Manual installation:

```bash
python3 -m venv backend/.venv
backend/.venv/bin/python -m pip install -r backend/requirements.txt
cd frontend
pnpm install --frozen-lockfile
cd ../backend
.venv/bin/python -m app.seed
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
```

In a second terminal:

```bash
cd frontend
pnpm dev
```

On Windows use `backend\.venv\Scripts\python.exe` and `backend\.venv\Scripts\uvicorn.exe` instead of their POSIX equivalents. `start.bat` handles these paths. For subsequent starts with installed dependencies, just run the two server commands above.

The default database is `backend/data/exam-lab.sqlite3`. Initialization migrates the schema and seeds the official blueprint and questions once. Edits and soft-deletions survive restarts. An alternate absolute database path can be set through the `SPLUNK_LAB_DB` environment variable before starting the backend. The root `.env.example` documents variables; it is not automatically loaded by the startup scripts. Vite reads `frontend/.env` for its proxy override.

## Features

- Dashboard with attempted answers, unique coverage, completed sessions, mean/best scores, accuracy, study streak, weighted readiness estimate, strongest/weakest domains, trend, recent results, and all 32 objective coverage records.
- Full mocks use 65 unique question IDs with saved timer deadlines, shuffled questions/options, single and multiple-response questions, review flags, navigator, submission confirmation, and resume. Full mocks never include correct-answer IDs or explanations in their active exam payloads.
- Quick practice supports 10/20/30/50 or custom counts, optional timer, immediate checked feedback or final feedback, and difficulty filtering. Checked answers lock to prevent changing them after seeing the solution.
- Topic sessions filter domains and exact objectives, prioritize low-accuracy domains (unattempted domains first), and optionally exclude previously answered questions. Domain and objective filters intersect. Requests exceeding the available matching bank return an actionable message rather than silently repeating questions.
- Results include exact-match scores, incorrect/unanswered counts, elapsed time, domain/objective breakdowns, selected/correct answers, per-option explanations, and documentation links. Incorrect questions can be retaken using their original snapshots, even if the bank entry changed.
- Wrong Answers records every historical missed/unanswered question that is still active in the bank, with repeated mistake counts. Bookmarks and personal revision notes persist in SQLite. Historical results remain available for deleted questions.
- Twelve SPL challenges cover completion, syntax repair, output prediction, command choice, scenario construction, and log interpretation. Deterministic supported answer strings accept whitespace normalization. They do not execute queries on a Splunk instance.
- Question Bank supports create/edit/soft-delete, text/domain/objective/difficulty filters, pagination, atomic JSON/CSV imports, exports, duplicate ID/stem detection, and review status. Unreviewed questions remain visible in the bank but are excluded from exams.
- Settings include duration, default count, unofficial target, dark/light mode, randomization, feedback, SQLite backup/restore, and progress reset with typed confirmation.

## Blueprint provenance

The user-mentioned PDF was not present among the attachments. The official PDF was downloaded from Splunk on 9 October 2026:

https://www.splunk.com/content/dam/splunk2/en_us/pdfs/training/splunk-test-blueprint-power-user.pdf

The unchanged PDF is in `references/`. Text extracted using pypdf is in `references/blueprint-extracted.txt`; `references/blueprint.json` records the exact 10 domains and 32 numbered sub-objectives. No supplementary scenarios are represented as additional official objectives.

The PDF specifies 65 questions and 60 total minutes including three minutes for the agreement, hence the default 57-minute answering timer. Practice duration is configurable and changing settings does not alter already-created deadlines.

Hamilton/largest-remainder rounding allocates `floor(65 × weight / 100)` then awards remaining seats to the largest fractional remainders, with lower domain IDs resolving ties:

| Domain | Weight | Bank | Full mock |
|---|---:|---:|---:|
| 1 | 5% | 15 | 3 |
| 2 | 10% | 30 | 7 |
| 3 | 15% | 45 | 10 |
| 4 | 10% | 30 | 7 |
| 5 | 10% | 30 | 7 |
| 6 | 10% | 30 | 7 |
| 7 | 10% | 30 | 6 |
| 8 | 10% | 30 | 6 |
| 9 | 10% | 30 | 6 |
| 10 | 10% | 30 | 6 |
| Total | 100% | 300 | 65 |

## Content review and limitations

The 300 original question records are derived from **100 authored concept cases, each with three related learning tasks**: choose a solution, evaluate its reasoning, and select both the solution and its supporting principle. They are 300 distinct stems, not 300 independent scenarios. Full mocks can contain related tasks from the same case. This supports repetition but can overestimate mastery; expanding with independently authored cases is a useful next improvement.

The author checked answers and rationales against primary Splunk documentation and the official blueprint. Structural validation covers unique IDs and stems, option IDs, answer cardinality, all 32 official objective mappings, and exact bank distribution. `question_bank/validation.json` records this audit. `verified` means author-reviewed against documentation; it does **not** mean official Splunk certification approval, independent subject-matter expert review, or execution in a real Splunk instance. Difficulty labels are editorial estimates. New/imported questions default to `needs_review` when no review status is supplied. In the editor, mark them reviewed only after checking both correct and incorrect option rationales.

No exam dumps were used as question content. The app is unaffiliated with Splunk. The default **80% score target is an unofficial study benchmark**, not an assertion about the official passing score. Readiness is the domain-weighted historical accuracy, with unattempted domains contributing zero. It is a study estimate rather than a pass predictor.

Duplicate detection normalizes punctuation, whitespace, and case in exact stems; it does not perform semantic duplicate detection. Challenge validation recognizes only the supported answer patterns shown after checking, so other valid equivalent SPL may be rejected. Streaks use UTC calendar days; display dates use the browser's locale/timezone. Domain coverage counts active bank entries answered in submitted sessions. Repeated attempts contribute to accuracy, while unique coverage does not double-count them. Unanswered items score incorrect, but are excluded from the answered-question accuracy denominator. Session scores include every item.

The local backend checks request origins, and CORS permits only the local frontend. There is no authentication by design. Keep both services bound to loopback. Docker uses 0.0.0.0 inside its private container network and publishes host ports on **127.0.0.1 only**. This is a personal practice tool, not a tamper-resistant examination environment: someone with direct access to the local bank/database can inspect solutions.

## Persistence, timers, and recovery

Exams store immutable JSON question snapshots in `exam_items`. Current bank editing never rewrites those snapshots. Options, answer keys, notes, settings, exam deadlines, answers and scored results live in SQLite, not browser localStorage.

Each answer is autosaved through the API before navigation. A failed save reports an error rather than silently claiming success. Submission uses a SQLite write transaction, refreshes session state, locks final answers, calculates the score, and persists all results together. Repeated submissions return the same result. The backend sweeps overdue sessions once per second while running; reads and writes also check expiry. If the app was stopped at the deadline, reopening submits overdue exams using the original deadline as completion time. Timed exams continue while another page is open. Browser clock skew is adjusted using the server timestamp.

Use **Settings → Download SQLite backup**. The SQLite backup API creates a consistent backup including WAL-backed updates. Restore verifies size/header, integrity, foreign keys, schema version, table definitions, exact official blueprint, question fingerprints, and snapshot structures before replacing the database. Invalid backups leave existing records intact. Restoration replaces all current data; take a backup first. Do not manually copy only the database while services are writing to it; use the backup endpoint or stop the services first.

Reset deletes progress, notes, bookmarks, and challenge attempts after typed confirmation. It preserves the question bank and preferences. Deleting a bank entry is a soft deletion. Retake uses stored snapshots.

## Question import format

JSON uses an array of question objects. Export an existing record as a template. Required fields: `id`, `domain_id`, `objective_id`, `text`, `type` (`single` / `multiple`), `options` (at least four objects with `id`, `text`, `explanation`), `correct` (option IDs), `explanation`, and `difficulty` (`easy` / `medium` / `hard`). Optional fields: `commands` (array), `reference` (official Splunk URL), and `review_status` (`verified` / `needs_review`).

CSV uses the same columns; encode `options`, `correct`, and `commands` as JSON strings inside CSV cells. Export produces properly quoted cells. Imports are limited to 5 MB and 2,000 records. Any invalid mapping, duplicate, or invalid answer aborts the entire import. Import adds records; use edit to update an existing ID.

## Tests and build

```bash
backend/.venv/bin/pytest -q backend/tests
cd frontend
pnpm test
pnpm build
pnpm exec playwright install chromium
pnpm e2e
```

Playwright starts isolated local test services on ports 8001/5174 with a temporary SQLite database. It never writes to your personal database. The POSIX default Python executable is `../backend/.venv/bin/python`; on Windows set `E2E_PYTHON=..\backend\.venv\Scripts\python.exe ..\backend\tests\run_e2e_server.py` before running `pnpm e2e`.

Tests cover weighted creation, blueprint/bank consistency, single and multiple-response scoring, deadlines, expiry, autosave/navigation, feedback concealment/locking, submissions, snapshot history, objective/difficulty/unanswered filters, imports, bookmarks/notes, repeated mistakes, analytics, settings, backups/restores, local origins, API errors and browser journeys. See `VERIFICATION.md` for the checks performed for this delivery.

## Optional Docker

```bash
docker compose up --build
```

The same local URL is served through nginx. Data persists in `backend/data`. Stop with `docker compose down`. The Compose configuration is included, but Docker startup was not exercised in this environment. Windows and Linux startup scripts were inspected; execution was verified on macOS using the equivalent server commands.

## Project structure

```text
splunk-exam-lab/
├── frontend/             # React UI, Vitest and Playwright tests
├── backend/
│   ├── app/              # FastAPI, models, validation, engine, seed
│   ├── migrations/       # Alembic versioned schema
│   ├── data/             # local SQLite database created on initialization
│   └── tests/            # isolated Pytest suite and browser-test API launcher
├── question_bank/        # authored cases, generator, 300 records, validation report
├── references/           # official PDF, extracted text, domain/objective JSON
├── docker-compose.yml
├── start.sh
├── start.bat
├── .env.example
└── README.md
```
