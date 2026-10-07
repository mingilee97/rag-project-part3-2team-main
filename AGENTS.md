# Shared main code

- Maintain only the runtime RFP RAG implementation and its execution settings.
- Do not add private work history, evaluation records, dashboards, reports, source documents, extracted content, answers, model files, credentials, or local environments.
- This repository has independent Git history. Do not merge the private source repository history.
- Keep Korean user-facing documentation and code comments. Read README.md and docs/인수인계.md before editing.
- Validate changes with `python test_core.py` and `git diff --check`. Do not call external models for these checks.
