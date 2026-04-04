# Runtime Adapter: OpenCode

Use this adapter when the skill runs in OpenCode or a similar agent shell.

This adapter assumes normal browse, file editing, and shell access. Native delegation and continuation may vary by OpenCode deployment, so this document defines the fallback order explicitly.

## Capability Mapping

### Parallel Deep-Dive Retrieval

- In `standard`, `deep`, and `ultradeep`, retrieval must include 2-3 focused deep-dive tracks in addition to broad search.
- If your OpenCode deployment exposes native delegation or concurrent task execution, use it.
- Otherwise, use the local orchestration helper and run isolated evidence tracks that are merged back into `sources.json`.
- Do not silently convert the run into a single shallow retrieval pass.

### Persona Red-Team Critique

- Always run these personas in `deep` and `ultradeep`:
  - `Skeptical Practitioner`
  - `Adversarial Reviewer`
  - `Implementation Engineer`
- Any critical gap found by the personas must trigger targeted delta queries before the report is considered complete.

### Automatic Continuation

- If the OpenCode deployment supports native follow-on execution, use it to continue from `continuation_state.json`.
- Otherwise resume with the local helper:

```bash
python scripts/research_engine.py --resume ./research_[YYYYMMDD]_[topic_slug]/run_state.json --runtime opencode
```

- Keep `continuation_state.json` only while continuation is active, and delete it after the final validated pass.

## Recommended Local Helper Flow

1. Start a run:

```bash
python scripts/research_engine.py --query "topic" --mode deep --runtime opencode
```

2. Write the report incrementally to `report.md` and maintain `sources.json`.
3. Let `run_state.json` serve as the durable checkpoint between passes.
4. If the report needs another pass, create `continuation_state.json` and resume through the helper if native continuation is unavailable.

## Failure Handling

- Do not silently skip parallel deep-dive retrieval because native delegation is missing.
- Do not silently stop after the first pass when continuation is required.
- If the environment lacks both native support and helper execution, stop and report a blocker instead of downgrading the workflow.
