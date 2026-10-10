# Delivery verification · 9 October 2026

Environment: macOS arm64, Python 3.9.6 virtual environment, Node.js 24.19.0, pnpm 11.25.0.

- Official PDF downloaded from Splunk, all three pages extracted and checked. Exactly 10 domains and 32 objectives stored; domain weights total 100%.
- Question-bank generator validates 300 distinct stems and IDs, correct answer cardinality, option IDs, exact objective mappings, full coverage, and domain distribution. The bank has 100 concept cases with three related tasks each; content review is by the author against primary documentation, without independent SME review or real Splunk query execution.
- Pytest: 20 tests passed. Covers weighted creation and concealment, saving/resuming, deadlines, background expiry, correct and exact multiple-response scoring, submission/history/analytics, immediate-feedback locking, filters, snapshot preservation, validation, atomic JSON/CSV import, bookmarks/notes/mistakes, backup/restore/reset, altered-blueprint rejection, preferences, challenges and origins.
- Vitest: 5 tests passed. Covers same-origin mutations, multipart boundaries, backend error propagation, unknown versus zero accuracy, and study-tool registration/validation/cleanup.
- Playwright: 4 end-to-end tests passed in isolated temporary SQLite storage. Covers all eleven pages, objective filtering, question editor opening, saved answers/flags/timers after refresh and resume, submission/review, bookmark/note persistence, challenge feedback, mobile navigation and dark/light mode.
- TypeScript compile and Vite production build passed. Vite reports a non-blocking bundle-size advisory because the chart library shares the main bundle.
- Local FastAPI and Vite servers run on 127.0.0.1:8000 and 127.0.0.1:5173. The delivery database contains 300 seeded questions; browser-test sessions use a separate disposable database.
- Desktop dashboard screenshot inspected at 1440×1050; mobile dashboard inspected in the in-app browser. Final screenshot: `references/dashboard.png`.
- WebMCP navigation and metrics tools registered in the live browser. Valid navigation visibly updated the page; invalid page input was rejected. Unsupported browsers simply omit registration.
- POSIX startup script passed shell syntax validation. Equivalent local server commands were exercised on macOS. Windows/Linux scripts and Docker files are provided, but Windows, Linux and Docker execution were not exercised.

See README for operating instructions, scoring definitions, backup semantics, and content limitations.

## Question bank update · 10 October 2026

- Reviewed 358 records: 300 authored questions and 58 playlist adaptations; 355 eligible for practice and three supplemental items excluded from examinations.
- Direct four-option single-answer bank, all 32 objectives covered, 1,432 option explanations, unique normalized stems, balanced shuffled base answer keys.
- Conservative one-time content upgrade preserves personal edits, soft deletions, revisions, and exam snapshots. Added tests for upgrade preservation, playlist eligibility and concealment, and CSV metadata round trips.
- Backend: 25 tests pass. TypeScript and Vite production build pass.
- Content was reviewed against primary documentation. No independent SME review or live Splunk query execution.
