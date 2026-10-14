# Shared main code

- Maintain only the runtime RFP RAG implementation and its execution settings.
- The user's 2026-10-14 request also authorizes the approved presentation files and the sanitized structure summary PDF. Keep the root navigation focused on Baseline and Version_1 through Version_4. Preserve required attribution in source records without names in version labels.
- Do not add private work history, evaluation records, dashboards, reports, source documents, extracted content, answers, model files, credentials, or local environments.
- This repository has independent Git history. Do not merge the private source repository history.
- Keep Korean user-facing documentation and code comments. Read README.md and Baseline/docs/인수인계.md before editing.
- Run runtime commands from Baseline. Validate changes with `python test_core.py`, `python -B -m unittest discover -s tests -v`, `python -B scripts/check_public.py`, and `git diff --check`. Do not call external models for these checks.
- Keep Anthropic keys empty in examples. Do not redistribute the four teammate sources until their permissions are confirmed. Do not merge or modify the separate modular repository.
