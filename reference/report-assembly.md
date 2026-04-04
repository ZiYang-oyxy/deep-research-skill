# Report Assembly: Progressive File Generation

## Length Requirements by Mode

| Mode | Target Words | Description |
|------|--------------|-------------|
| Quick | 2,000-4,000 | Baseline quality threshold |
| Standard | 4,000-8,000 | Comprehensive analysis |
| Deep | 8,000-15,000 | Thorough investigation |
| UltraDeep | 15,000-20,000+ | Maximum rigor |

---

## Output Safeguard

Practical output limits vary by environment. Keep each generated section small enough that it can be reviewed, cited, and written cleanly in one pass.

**Practical limits:**
- Keep each individual generation under roughly 2,000 words
- Generate the report section by section
- Use continuation when the report grows beyond a comfortable single-pass size
- When continuation is required, persist handoff state and provide an explicit resume target for the next pass

---

## Progressive Section Generation

**Core strategy:** Generate one section at a time and append it to the report. This avoids large single-pass outputs and preserves citation integrity.

### Phase 8.1: Setup

Create a dedicated report directory in the current working directory:

```bash
mkdir -p ./research_[YYYYMMDD]_[topic_slug]
```

Initialize these files inside the directory:

- `report.md` - the main report
- `sources.json` - source and citation ledger
- `run_state.json` - checkpoint state, section progress, and runtime metadata
- `continuation_state.json` - only if continuation becomes necessary

### Phase 8.2: Section Generation Loop

**Pattern:** Generate section -> append to `report.md` -> refresh source ledger -> move to next section.

Each write should contain one complete section.

After appending new content, re-run the helper with `--resume` so it can refresh section checkpoints, rebuild `sources.json` from bibliography and cited snippets, recompute `next_sections`, update `metadata.next_action`, and update continuation state.

If the report no longer fits comfortably in the current pass:

1. Update `run_state.json`
2. Write `continuation_state.json`
3. Continue with the resume target recorded in `metadata.next_action`
4. Treat the report as incomplete until the continuation chain finishes

**Initialize citation tracking:**

```bash
printf '[]\n' > ./research_[YYYYMMDD]_[topic_slug]/sources.json
```

Update `sources.json` after each section. Each entry should include at least:

```json
{
  "num": 1,
  "title": "Source title",
  "url": "https://...",
  "claim": "claim supported by this citation",
  "evidence_quote": "exact quote or precise paraphrase"
}
```

**Section sequence:**

1. **Executive Summary** (50-400 words)
   - Create the file and write the opening section
   - Add citations immediately
2. **Introduction** (400-800 words)
   - Append to `report.md`
3. **Finding 1-N** (600-2,000 words each)
   - Append each finding separately
4. **Synthesis & Insights**
   - Go beyond summary; connect evidence into implications
5. **Limitations & Caveats**
   - Document counterevidence, gaps, and uncertainty
6. **Recommendations**
   - Immediate actions, next steps, and additional research needs
7. **Bibliography**
   - Include every citation used in the body
8. **Appendix: Methodology**
   - Document process, coverage, and verification approach

---

## File Organization

**Report directory:**

- Location: `./research_[YYYYMMDD]_[topic_slug]/`
- Keep all run-specific artifacts for one report inside this directory

**Default file names:**

- `report.md`
- `sources.json`
- `run_state.json`
- `continuation_state.json` when needed

If additional working files are useful for the environment, keep them in the same directory and name them clearly.

---

## Word Count Per Section

**Critical rule:** No single generation should try to write an oversized block of content.

Example:

- 10 findings x 1,500 words = 15,000 words total
- Each generation still writes only one finding at a time
- The assembled file can be large even when each generation remains manageable
