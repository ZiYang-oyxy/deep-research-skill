---
name: deep-research
description: >
  Conducts enterprise-grade research with multi-source synthesis, citation
  tracking, contract gating, and resumable markdown-first report assembly. The
  local helper defaults to skeleton-only initialization: it mainly creates
  phase artifacts, state files, and a report skeleton rather than automatically
  finishing retrieval, writing, and artifact backfill. Triggers on "deep
  research", "comprehensive analysis", "research report", "compare X vs Y",
  "analyze trends", or "state of the art". Not for simple lookups, debugging,
  or questions answerable with 1-2 searches.
---

# Deep Research

## Core Purpose

Deliver citation-backed, verified research reports through a structured pipeline with durable evidence tracking, progressive context management, and resumable markdown-first packaging.

**Default report language:** Final reports should use Chinese section headings and Chinese narrative by default. Existing English headings remain valid as compatible input for validation and resume.

**Autonomy Principle:** Operate independently. Infer reasonable assumptions from context. Pause only for critical blockers, contradictory requirements, or missing access.

**Non-Silent Degradation Rule:** The skill must not silently drop parallel deep-dive retrieval, persona red-team critique, or continuation handoff. If the current runtime cannot satisfy one of these directly, use the local orchestration helper or stop and report the blocker explicitly.

---

## Decision Tree

```text
Request Analysis
+-- Simple lookup? --> STOP: Use a normal browse/search workflow
+-- Debugging or implementation task? --> STOP: Use standard coding/debugging workflow
+-- Complex analysis or synthesis needed? --> CONTINUE

Mode Selection
+-- Initial exploration --> quick (3 phases, 2-5 min)
+-- Standard research --> standard (6 phases, 5-10 min) [DEFAULT]
+-- Critical decision --> deep (8 phases, 10-20 min)
+-- Comprehensive review --> ultradeep (8+ phases, 20-45 min)
```

**Default assumptions:** Technical query = technical audience. Comparison = balanced perspective. Trend = recent 12-24 months unless the prompt sets a wider window.

---

## Workflow Overview

| Phase | Name | Quick | Standard | Deep | UltraDeep |
|-------|------|-------|----------|------|-----------|
| 1 | SCOPE | Y | Y | Y | Y |
| 2 | PLAN | - | Y | Y | Y |
| 3 | RETRIEVE | Y | Y | Y | Y |
| 4 | TRIANGULATE | - | Y | Y | Y |
| 4.5 | OUTLINE REFINEMENT | - | Y | Y | Y |
| 5 | SYNTHESIZE | - | Y | Y | Y |
| 6 | CRITIQUE | - | - | Y | Y |
| 7 | REFINE | - | - | Y | Y |
| 8 | PACKAGE | Y | Y | Y | Y |

---

## Execution

**On invocation, load relevant reference files:**

1. **Phase 1-7:** Load [methodology.md](./reference/methodology.md) for detailed phase instructions
2. **Phase 8 (Report):** Load [report-assembly.md](./reference/report-assembly.md) for progressive generation
3. **Quality checks:** Load [quality-gates.md](./reference/quality-gates.md)
4. **Long reports (>18K words):** Load [continuation.md](./reference/continuation.md)
5. **Runtime adapter:** Load [runtime-codex.md](./reference/runtime-codex.md) or [runtime-opencode.md](./reference/runtime-opencode.md) when running in that environment

**Templates:**
- Report structure: [report_template.md](./templates/report_template.md)

**Scripts:**
- `python scripts/research_engine.py --query [topic] --mode [mode] --runtime [codex|opencode|generic]`
- `python scripts/research_engine.py --query [topic] --mode [mode] --runtime [codex|opencode|generic] --skeleton-only`
- `python scripts/research_engine.py --query [topic] --mode [mode] --runtime [codex|opencode|generic] --attempt-autowrite`
- `python scripts/research_engine.py --query [topic] --mode [mode] --runtime [codex|opencode|generic] --auto-continue`
- `python scripts/research_engine.py --resume ./research_[YYYYMMDD]_[topic_slug]/run_state.json --runtime [codex|opencode|generic]`
- `python scripts/research_engine.py --resume ./research_[YYYYMMDD]_[topic_slug]/continuation_state.json --runtime [codex|opencode|generic]`
- `python scripts/validate_report.py --report [path]`
- `python scripts/verify_citations.py --report [path]`
- `python scripts/source_evaluator.py`

---

## Non-Negotiable Capabilities

**1. Parallel Deep-Dive Retrieval**

- In `standard`, `deep`, and `ultradeep` modes, retrieval must include 2-3 focused deep-dive tracks beyond broad search.
- Preferred execution order: native runtime delegation/subagents -> local orchestration helper -> explicit blocker.
- Do not silently collapse to a single shallow retrieval pass.

**2. Persona Red-Team Critique**

- In `deep` and `ultradeep` modes, critique must include these personas:
  - `Skeptical Practitioner`
  - `Adversarial Reviewer`
  - `Implementation Engineer`
- If critique exposes a critical knowledge gap, run targeted delta queries before final packaging.

**3. Continuation Handoff**

- When the report no longer fits comfortably in one pass, persist `continuation_state.json` and continue through native runtime support or an explicit helper resume.
- Preferred execution order: native runtime continuation/delegation -> local orchestration helper -> explicit blocker.
- Do not return a partial report as if it were complete.

---

## Output Contract

`research_engine.py` should be treated as an orchestration helper, not a fully automatic report writer. In most runtimes it mainly generates phase artifacts, status files, and the report skeleton. Actual retrieval, analysis, prose drafting, and artifact backfill usually still need to be performed by the current agent or delegated subagents.

**Required sections:**
- Executive Summary (50-400 words)
- Introduction (scope, methodology, assumptions)
- Main Analysis (4-8 findings, 600-2,000 words each, cited)
- Synthesis & Insights (patterns, implications)
- Limitations & Caveats
- Recommendations
- Bibliography (COMPLETE - every citation, no placeholders)
- Appendix: Methodology

**Output directory:** `./research_[YYYYMMDD]_[topic_slug]/`

**Expected files:**
- `report.md` - primary deliverable
- `sources.json` - durable source ledger and citation metadata
- `run_state.json` - checkpoint state, section progress, next-section batch, and runtime metadata for resume/orchestration
- `continuation_state.json` - only when the report spans multiple passes
- `phase_scope.json` - capability contract artifact for research framing quality
- `phase_plan.json` - capability contract artifact for research roadmap quality
- `phase_retrieve.json` - capability contract artifact for parallel deep-dive retrieval
- `phase_triangulate.json` - capability contract artifact for claim verification and contradiction tracking
- `phase_outline_refinement.json` - capability contract artifact for evidence-driven outline updates
- `phase_synthesize.json` - capability contract artifact for synthesis quality and argument formation
- `phase_critique.json` - capability contract artifact for persona critique and delta-query loop
- `phase_refine.json` - capability contract artifact for critique follow-up and gap closure

**Quality standards:**
- 10+ sources, 3+ per major claim
- All factual claims cited immediately as `[N]`
- No placeholders, no fabricated citations
- Prose-first (>=80%), bullets used sparingly
- `deep` and `ultradeep` must include persona-based red-team critique before delivery

**Optional helpers and extensions:**
- `source_evaluator.py` can be used when the runtime wants explicit source scoring

---

## Environment Assumptions

This skill assumes the current agent environment can do the following:

- Search the web or another current-information source
- Open and read individual source pages
- Run local shell commands and repository scripts
- Create and edit files in the working directory
- Either provide native delegation/continuation primitives, or allow the skill to call the local orchestration helper

Optional niceties may degrade gracefully. The three non-negotiable capabilities above may not.

---

## When to Use / NOT Use

**Use:** Comprehensive analysis, technology comparisons, state-of-the-art reviews, multi-perspective investigation, market analysis, strategy support.

**Do NOT use:** Simple lookups, debugging, 1-2 search answers, quick time-sensitive queries with shallow scope.
