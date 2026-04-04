# Auto-Continuation Protocol

## When to Use

Use continuation when the report becomes too large or too detailed to finish comfortably in a single pass.

Typical triggers:

- Report exceeds roughly 18,000 words
- Too many findings remain for one clean generation pass
- Citation tracking is becoming error-prone without an intermediate handoff

**Hard requirement:** Continuation is not a manual convenience feature. If continuation is needed, the workflow should keep going until the report is complete unless the runtime or local helper is genuinely blocked.

---

## State Files

**Always present:**

- `./research_[YYYYMMDD]_[topic_slug]/run_state.json` - checkpoint state, phase results, section checkpoints, next-section batch, and resume entry point

**Only when continuation is active:**

- `./research_[YYYYMMDD]_[topic_slug]/continuation_state.json` - active handoff state for the next pass

---

## Strategy Overview

1. Generate the completed sections that fit in the current pass.
2. Save or refresh `run_state.json`.
3. If another pass is required, write `continuation_state.json`.
4. Trigger the next pass automatically through the current runtime or the local orchestration helper.
5. Continue until the bibliography and methodology appendix are complete.
6. Validate the finished report, refresh `sources.json`, and delete `continuation_state.json`.

---

## Runtime Resolution Order

Resolve continuation in this order:

1. Native runtime continuation or delegated follow-on execution
2. Local orchestration helper via either:
   - `python scripts/research_engine.py --resume ./research_[YYYYMMDD]_[topic_slug]/run_state.json --runtime [codex|opencode|generic]`
   - `python scripts/research_engine.py --resume ./research_[YYYYMMDD]_[topic_slug]/continuation_state.json --runtime [codex|opencode|generic]`
3. Explicit blocker if neither path is available

Do not silently stop after pass one when continuation is required. If native continuation is unavailable, use the explicit helper resume path.

---

## Continuation State File

**Location:** `./research_[YYYYMMDD]_[topic_slug]/continuation_state.json`

```json
{
  "version": "2.1.1",
  "report_id": "[unique_id]",
  "file_path": "./research_[YYYYMMDD]_[topic_slug]/report.md",
  "mode": "[quick|standard|deep|ultradeep]",
  "progress": {
    "sections_completed": ["list of section IDs"],
    "total_planned_sections": 15,
    "word_count_so_far": 12000,
    "continuation_count": 1
  },
  "citations": {
    "used": [1, 2, 3],
    "next_number": 45,
    "bibliography_entries": [
      "[1] Full citation entry",
      "[2] Full citation entry"
    ]
  },
  "research_context": {
    "research_question": "[original question]",
    "key_themes": ["theme1", "theme2"],
    "main_findings_summary": [
      "Finding 1: [100-word summary]",
      "Finding 2: [100-word summary]"
    ],
    "narrative_arc": "middle"
  },
  "quality_metrics": {
    "avg_words_per_finding": 1500,
    "citation_density": 5.2,
    "prose_vs_bullets_ratio": "85% prose",
    "writing_style": "technical-precise-data-driven"
  },
  "run_state_path": "./research_[YYYYMMDD]_[topic_slug]/run_state.json",
  "next_sections": [
    {"id": "finding_3", "type": "finding", "title": "Finding 3", "target_words": 1500, "heading": "### Finding 3: [Title]", "status": "pending"},
    {"id": "synthesis_insights", "type": "synthesis", "title": "Synthesis & Insights", "target_words": 1000, "heading": "## Synthesis & Insights", "status": "pending"}
  ]
}
```

---

## Resume Protocol

When resuming a report:

1. Read `continuation_state.json` or `run_state.json`.
2. If the entry file is `continuation_state.json`, load the sibling `run_state.json`.
3. Read the existing `report.md`.
4. Refresh section checkpoints from the current `report.md`.
5. Review the last 2-3 completed sections for style and flow.
6. Resume citation numbering from `citations.next_number`.
7. Generate only the sections listed in `next_sections`.
8. Update `report.md`, `sources.json`, `run_state.json`, `metadata.next_action`, and `continuation_state.json` after each completed section.

---

## Continuation Quality Protocol

### Context Loading

Before generating more content:

1. Load the saved research context.
2. Re-read the latest completed sections.
3. Reconstruct the narrative arc.
4. Confirm citation numbering and bibliography continuity.
5. Confirm whether the next pass is running through a native runtime adapter or the local helper.

### Pre-Generation Checklist

- [ ] Research context loaded
- [ ] Prior sections reviewed
- [ ] Citation numbering resumed correctly
- [ ] Quality targets understood
- [ ] Remaining sections prioritized

### Per-Section Generation

1. Generate one section.
2. Check word count, citation density, prose ratio, and theme alignment.
3. If the section fails quality standards, regenerate before appending.
4. Append the accepted section to `report.md`.
5. Re-run the helper to refresh `sources.json`, `run_state.json`, and `continuation_state.json`.

### Handoff Decision

Calculate whether the remaining sections still fit in the current pass:

- If yes, finish the report and remove `continuation_state.json`
- If no, stop at the next clean section boundary, save an updated continuation state, and use the recorded resume command for the next pass

---

## Final Pass Responsibilities

The final continuation pass must:

- Generate all remaining content sections
- Generate the complete bibliography
- Re-run the helper so `sources.json` is refreshed from bibliography and cited snippets
- Validate the assembled report with `python scripts/validate_report.py --report [path]`
- Verify citations with `python scripts/verify_citations.py --report [path]`
- Refresh `run_state.json` with the completed status
- Delete `continuation_state.json` after the report is complete

---

## Blocker Rule

If the runtime cannot continue on its own and the local helper cannot be executed, stop and report a blocker explicitly. Do not mark the report as complete.

---

## User Communication

When handing off to another automatic pass, communicate:

```text
Report generation reached a clean section boundary.
Progress: [X sections complete, Y words total]
Next sections: [section list]
State saved to: ./research_[YYYYMMDD]_[topic_slug]/continuation_state.json
Auto-continuing via native runtime or local helper.
```
