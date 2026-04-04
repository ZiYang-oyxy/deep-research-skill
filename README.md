# Deep Research Skill

Enterprise-grade research skill for agent environments that can browse current sources, open source pages, edit files, and run local scripts. It produces citation-backed research reports with durable citation tracking, resumable markdown-first report assembly, automated validation, and runtime-aware orchestration.

## Installation

```bash
git clone https://github.com/199-biotechnologies/claude-deep-research-skill.git
```

Place the repository in the skills location used by your agent environment, or vendor it into your workspace and load `SKILL.md` from there.

No additional dependencies are required for the default Markdown-only workflow.

### Optional: `search-cli`

If your environment benefits from a CLI-based aggregated search workflow, `search-cli` is still supported as an optional helper:

```bash
brew tap 199-biotechnologies/tap && brew install search-cli
search config set keys.brave YOUR_KEY
```

This is optional. The skill is written to work with whatever current-information search and browsing capabilities your environment already provides.

## Usage

Examples of requests that should trigger this skill:

```text
deep research on the current state of quantum computing
```

```text
deep research in ultradeep mode: compare PostgreSQL vs Supabase for our stack
```

## Research Modes

| Mode | Phases | Duration | Best For |
|------|--------|----------|----------|
| Quick | 3 | 2-5 min | Initial exploration |
| Standard | 6 | 5-10 min | Most research questions |
| Deep | 8 | 10-20 min | Complex topics, critical decisions |
| UltraDeep | 8+ | 20-45 min | Comprehensive reports, maximum rigor |

## Pipeline

Scope -> Plan -> Retrieve -> Triangulate -> Outline Refinement -> Synthesize -> Critique -> Refine -> Package

Key features:

- Current-date awareness before time-sensitive searches
- Parallel or batched retrieval across 5-10 independent search angles
- Mandatory parallel deep-dive tracks in `standard`, `deep`, and `ultradeep`
- First Finish Search thresholds by mode
- Evidence normalization for synthesis and citation stability
- Mandatory persona-based red-team critique in `deep` and `ultradeep`
- Disk-persisted source tracking in `sources.json`
- Durable phase and section checkpoints in `run_state.json`
- Continuation support for long reports through `continuation_state.json`
- Continuation handoff via native runtime support when available, otherwise explicit helper resume
- Final completion gated by `validate_report.py` and `verify_citations.py`
- Validation loop with structure and citation checks

## Output

Each report is written to a dedicated subdirectory in the current working directory:

```text
./research_[YYYYMMDD]_[topic_slug]/
```

Default files:

- `report.md` - primary deliverable
- `sources.json` - source ledger auto-refreshed from bibliography and cited snippets
- `run_state.json` - phase results, section checkpoints, next-section batch, validation status, and runtime metadata
- `continuation_state.json` - generated only when the report spans multiple passes

Contract artifacts for non-silent-degradation checks:

- `phase_scope.json` - required in all modes
- `phase_plan.json` - required in `standard`, `deep`, and `ultradeep`
- `phase_retrieve.json` - required in `standard`, `deep`, and `ultradeep`
- `phase_triangulate.json` - required in `standard`, `deep`, and `ultradeep`
- `phase_outline_refinement.json` - required in `standard`, `deep`, and `ultradeep`
- `phase_synthesize.json` - required in `standard`, `deep`, and `ultradeep`
- `phase_critique.json` - required in `deep` and `ultradeep`
- `phase_refine.json` - required in `deep` and `ultradeep`

HTML and PDF assets remain in the repository as optional non-default resources, but the main skill workflow does not generate them.

Optional helper automation:

- Add `--auto-continue` to keep the helper running while another agent or manual editor updates `report.md` / `phase_*.json`
- The helper watches the files listed in `metadata.next_action.required_files` and consumes the recorded `resume_command` automatically when changes land
- Tune with `--auto-continue-timeout`, `--auto-continue-poll`, and `--auto-continue-max-resumes`

## Quality Standards

- 10+ sources, or fewer only when explicitly documented in limitations
- 3+ sources per major claim when available
- Executive summary 50-400 words
- Findings 600-2,000 words each, prose-first (>=80%)
- Full bibliography with URLs and no placeholders
- `deep` and `ultradeep` require persona-based red-team critique before delivery
- Validation with `validate_report.py` and `verify_citations.py`
- Validation loop: validate -> fix -> retry, up to 3 cycles

## Environment Expectations

This skill assumes the environment can:

- Search the web or another current-information source
- Open and inspect source pages
- Run shell commands and repository scripts
- Create and edit files in the working directory
- Either expose native delegation/continuation support, or allow the local helper to be executed

Normal retrieval and packaging details can degrade gracefully. Mandatory parallel deep-dive retrieval, persona red-team critique, and continuation handoff may not be silently downgraded.

## Runtime Adapters

Use the runtime adapter that matches the current environment:

- [reference/runtime-codex.md](./reference/runtime-codex.md)
- [reference/runtime-opencode.md](./reference/runtime-opencode.md)

If the runtime lacks native delegation or continuation, fall back to the local helper:

```bash
python scripts/research_engine.py --query "topic" --mode deep --runtime codex
python scripts/research_engine.py --resume ./research_[YYYYMMDD]_[topic_slug]/run_state.json --runtime codex
python scripts/research_engine.py --resume ./research_[YYYYMMDD]_[topic_slug]/continuation_state.json --runtime codex
```

## Optional Search Approaches

The skill no longer assumes any single built-in search tool. Typical compatible approaches include:

- Native search/browse tooling provided by the agent environment
- `search-cli` for aggregated provider search
- Manual browsing of source pages once promising results are identified

The retrieval methodology is tool-agnostic by design.

## Architecture

```text
deep-research/
├── SKILL.md
├── reference/
│   ├── methodology.md
│   ├── report-assembly.md
│   ├── quality-gates.md
│   ├── continuation.md
│   ├── runtime-codex.md
│   ├── runtime-opencode.md
│   ├── html-generation.md
│   └── weasyprint_guidelines.md
├── templates/
│   ├── report_template.md
│   └── mckinsey_report_template.html
├── scripts/
│   ├── report_contract.py
│   ├── validate_report.py
│   ├── verify_citations.py
│   ├── source_evaluator.py
│   ├── citation_manager.py
│   ├── md_to_html.py
│   ├── verify_html.py
│   └── research_engine.py
└── tests/
    └── fixtures/
```

Notes:

- `SKILL.md` is the entry point and defines the default workflow.
- `reference/html-generation.md` and `reference/weasyprint_guidelines.md` are retained as optional assets, not default deliverables.
- `scripts/report_contract.py` is the shared source of truth for required section headings and validator thresholds.
- `scripts/research_engine.py` creates the report directory in the current working directory, maintains section checkpoints inside `run_state.json`, records `metadata.next_action`, and can resume from either `run_state.json` or `continuation_state.json`.

## Validation

```bash
python scripts/validate_report.py --report ./research_[YYYYMMDD]_[topic_slug]/report.md
python scripts/verify_citations.py --report ./research_[YYYYMMDD]_[topic_slug]/report.md
```

Example smoke test for the orchestration helper:

```bash
python scripts/research_engine.py --query "state of quantum computing 2026" --mode deep --runtime codex
python scripts/research_engine.py --query "state of quantum computing 2026" --mode deep --runtime codex --auto-continue
```

To refresh section checkpoints after writing more report content:

```bash
python scripts/research_engine.py --resume ./research_[YYYYMMDD]_[topic_slug]/run_state.json --runtime codex
```

Default test command:

```bash
python -m unittest discover -s tests -p 'test_*.py'
```

## License

MIT - modify as needed for your workflow.
