# Cursor prompt — extend this starter without changing its privacy model

I have an existing Python project called `marriage-profile-filter` with `core.py`, `dashboard.py`, `bot.py`, `reports.py`, `import_history.py`, test files and docs. Read every existing file and work incrementally.

Project objective: private mobile-friendly Telugu/English marriage profile filtering for OLD, legitimately permissioned Telegram JSON exports and FUTURE, consent-based voluntary Telegram bot submissions. Extract bride name, age, DOB, nakshatram, rashi, time/place of birth, education and present location; match user filters; export XLSX, DOCX and PDF. Source names/IDs must remain visible and possible duplicates flagged. Never invent missing values.

Hard privacy rules:
- Do not silently scrape public or private Telegram group messages, gather arbitrary group history, or bypass privacy mode or platform restrictions.
- Keep default ingestion limited to explicitly permission-confirmed old exports and opt-in `/submit CONSENT:YES` messages in DM or allowlisted groups.
- Do not train/fine-tune AI models on Telegram profiles or send identifiable messages to external LLMs without proper legal permission and separately informed consent.
- Minimize collected data, never collect phone numbers or government IDs, respect deletion/revocation and do not expose the dashboard publicly without auth.

Implementation tasks:
1. Review schema, parser, aliases, deduplication, match function and tests. Add fixture-based parser tests for Telugu labels, English variants, absent ages, invalid DOB, duplicate names, formula-injection-like input, consent-gate failures.
2. Add `review_status` and a human correction UI with history and ability to delete/revoke, preserving original message reference (not raw personal text).
3. Add dashboard private authentication, role restrictions, local encrypted backups, inactivity session timeout, privacy notice and retention-based deletion.
4. Support all 27 Nakshatram spelling variants (Telugu/English transliterations) with reviewed dictionaries.
5. Add authenticated phone access via Tailscale/private deployment, no unsecured public Streamlit server.
6. Add explicit, user-configured alert rules and safe Telegram direct-message summaries with no personal contact data.
7. Add UI and unit/integration tests; preserve and test Excel/Word/PDF exports, including Telugu font rendering.
8. Optional OCR for *voluntarily submitted, permissioned* image/PDF biodata only. Default OFF and local; label confidence and require human review.

Start with a repository inspection and provide a tested change set (not an unreviewed rewrite). Clearly differentiate complete features from future work.
