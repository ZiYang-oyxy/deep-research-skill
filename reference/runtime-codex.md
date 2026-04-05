# Runtime Adapter: Codex

Use this adapter when the skill runs in a Codex-style environment with shell, file editing, browsing, and parallel tool access.

## Capability Mapping

### Parallel Deep-Dive Retrieval

- Prefer native parallel tool calls for broad retrieval.
- For `standard`, `deep`, and `ultradeep`, run 2-3 focused deep-dive tracks in parallel:
  - Primary-source or academic extraction
  - Counterevidence and limitations review
  - Implementation, commercial, or domain-specific validation
- If native delegation is unavailable in the current Codex deployment, keep the broad retrieval in the main session and use the local orchestration helper plus isolated evidence tracks. Do not silently skip the deep dives.

### Persona Red-Team Critique

- Run the persona critique in the main session after synthesis:
  - `Skeptical Practitioner`
  - `Adversarial Reviewer`
  - `Implementation Engineer`
- If any persona identifies a critical evidence gap, return to targeted retrieval before final packaging.

### Automatic Continuation

- Prefer native continuation or delegated follow-on passes if the runtime exposes them.
- Otherwise use the local helper and resume from the saved run state:

```bash
python scripts/research_engine.py --resume ./research_[YYYYMMDD]_[topic_slug]/run_state.json --runtime codex
```

- When continuation is active, keep `continuation_state.json` updated until the report is complete, then remove it.

## Recommended Local Helper Flow

1. Start a run:

```bash
python scripts/research_engine.py --query "topic" --mode deep --runtime codex
python scripts/research_engine.py --query "topic" --mode deep --runtime codex --skeleton-only
python scripts/research_engine.py --query "topic" --mode deep --runtime codex --attempt-autowrite
```

2. Treat the helper as skeleton-first by default: it mainly prepares `report.md`, `sources.json`, `run_state.json`, and the phase artifacts.
3. Actual retrieval, analysis, and narrative drafting normally still happen in the active agent session or delegated subagents.
4. If another pass is required, write `continuation_state.json` and re-enter through the helper or native continuation.

## Failure Handling

- Missing native delegation is not an excuse to skip parallel deep-dive retrieval.
- Missing native continuation is not an excuse to hand back a partial report; use the helper's recorded resume path instead.
- If neither native support nor the local helper can be used, stop and report a blocker explicitly.
