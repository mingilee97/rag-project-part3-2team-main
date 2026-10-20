# FINAL-02 submission

- The user's approved 2026-10-20 scope replaces old executable versions with FINAL-02. Preserve Git history and history documents, source records, reports and journals. The later approved scope removes legacy presentations/ and baseline-main-snapshot.json from the current tree, preserving them in Git history and local originals.
- Maintain only the final RFP RAG runtime and its configuration. Do not revive Baseline/Main/Version selectors.
- Never publish original RFPs, parsed text, metadata rows, benchmark questions, answers, checkpoints, keys, vector stores, model weights, private activity or environments.
- Keep existing attribution and rights notices. Do not invent a license. The supplied archive credits 이원영 and 김현경 final_pipeline at abbreviated commit 7db81eb; this is a source claim, not a verified remote commit.
- Korean for user-facing documentation and comments. Run python -B -m unittest discover -s tests -v and git diff --check. Tests must use synthetic fixtures, no network, no model downloads and no paid API calls.
- README.md, docs/기술리포트목록.md, docs/출처와변경.md and docs/인수인계.md describe the current state.
- Do not change repository access, invitations, hosting or Git history. No force push.
