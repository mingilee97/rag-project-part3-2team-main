# Shared main code

- Maintain only the runtime RFP RAG implementation and its execution settings.
- The user's 2026-10-14 request also authorizes the approved presentation files and the sanitized structure summary PDF. Keep the root navigation focused on Baseline and Version_1 through Version_4. Preserve required attribution in source records without names in version labels.
- Do not add private work history, evaluation records, dashboards, reports, source documents, extracted content, answers, model files, credentials, or local environments.
- This repository has independent Git history. Do not merge the private source repository history.
- Keep Korean user-facing documentation and code comments. Read README.md and Baseline/docs/인수인계.md before editing.
- Run runtime commands from Baseline. Validate changes with `python test_core.py`, `python -B -m unittest discover -s tests -v`, `python -B scripts/check_public.py`, and `git diff --check`. Do not call external models for these checks.
- Keep Anthropic keys empty in examples. The user explicitly approved including the four teammate source bundles on 2026-10-14 after hearing the license concern. Preserve original attribution, fixed SHAs, and existing rights notices; do not invent a license. Do not merge or modify the separate modular repository.
- Baseline is the preserved reference. Main starts as an independent byte-identical copy for team changes; do not use symlinks or hardlinks. Run candidate checks with `python -B test_versions.py` from the repository root. Candidate entrypoints use the included modules and root version_runtime.py; they require no external source copy.
