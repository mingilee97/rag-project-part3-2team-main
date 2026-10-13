# Shared main code

- Maintain only the runtime RFP RAG implementation and its execution settings.
- Do not add private work history, evaluation records, dashboards, reports, source documents, extracted content, answers, model files, credentials, or local environments.
- The user's 2026-10-09 request authorizes a separate review branch with sanitized UI utilities, public teammate components, aggregate measurements, version catalogs, and offline reproducibility tools. Keep private evaluation rows, document or question texts, team metadata, answers, databases, model files, and credentials out of this scope. Do not deploy or adopt candidates automatically.
- This repository has independent Git history. Do not merge the private source repository history.
- Keep Korean user-facing documentation and code comments. Read README.md and docs/인수인계.md before editing.
- Validate changes with `python test_core.py` and `git diff --check`. Do not call external models for these checks.
