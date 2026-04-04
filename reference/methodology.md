# Deep Research Methodology: 8-Phase Pipeline

## Overview

This document defines the deep-research workflow used to gather, verify, and synthesize information from multiple sources. The phases are sequential by default, but evidence discovered in later phases may require returning to retrieval or outline refinement.

Three capabilities are non-negotiable in the default workflow:

- Parallel deep-dive retrieval in `standard`, `deep`, and `ultradeep`
- Persona-based red-team critique in `deep` and `ultradeep`
- Continuation handoff when the report outgrows one clean pass

---

## Phase 1: SCOPE - Research Framing

**Objective:** Define research boundaries and success criteria.

**Activities:**
1. Decompose the question into core components.
2. Identify stakeholder perspectives.
3. Define scope boundaries.
4. Establish success criteria.
5. List assumptions that require validation.

**Reasoning guidance:** Explore multiple framings before committing to scope.

**Output:** Structured scope with boundaries, audience, risks, and assumptions.

**Artifact contract:** Persist framing evidence in `phase_scope.json`. The helper requires non-empty `core_components`, `in_scope`, `success_criteria`, and `assumptions`.

---

## Phase 2: PLAN - Strategy Formulation

**Objective:** Create an efficient research roadmap.

**Activities:**
1. Identify primary and secondary source types.
2. Map knowledge dependencies.
3. Draft 5-15 search query variants.
4. Plan how claims will be triangulated.
5. Estimate time and effort by phase.
6. Define quality gates for moving forward.

**Reasoning guidance:** Branch into multiple viable research paths, then converge on the best path.

**Output:** Research plan with prioritized investigation paths and verification strategy.

**Artifact contract:** Persist planning evidence in `phase_plan.json`. The helper requires non-empty `primary_source_types`, at least 5 `search_queries`, plus explicit `triangulation_strategy` and `quality_gates`.

---

## Phase 3: RETRIEVE - Parallel Information Gathering

**Objective:** Systematically collect information from multiple source types as quickly as possible without sacrificing quality.

**Critical rule:** Use the current environment's available browse/search capabilities aggressively, and batch independent searches when the tooling allows it.

**Runtime adaptation rule:** In `standard`, `deep`, and `ultradeep`, you must also run 2-3 focused deep-dive tracks. Resolve this requirement in order:

1. Native runtime delegation or subagents
2. Local orchestration helper and isolated evidence tracks
3. Explicit blocker if neither path is available

Do not silently skip the deep-dive tracks.

**Artifact contract:** Persist completion evidence in `phase_retrieve.json`. The helper treats the contract as satisfied only when the artifact records broad retrieval plus at least 2 completed deep-dive tracks with non-zero evidence counts.

### Query Decomposition Strategy

Before launching searches, break the question into 5-10 independent angles:

1. **Core topic** - Meaning-based exploration of the central concept
2. **Technical details** - Specific terms, APIs, implementations, mechanisms
3. **Recent developments** - What changed in the last 12-18 months
4. **Academic/formal sources** - Papers, standards, formal evaluations
5. **Alternative perspectives** - Competing approaches and criticisms
6. **Data sources** - Quantitative evidence, metrics, benchmarks
7. **Industry/commercial analysis** - Adoption, market movement, vendor claims
8. **Failure modes and limitations** - Known problems, edge cases, and risks

### Retrieval Protocol

**Step 0: Get the current date**

Before any time-sensitive search, retrieve today's date from the environment and use that exact date or year in recentness-sensitive queries. Do not assume the current year from prior context.

**Step 1: Launch broad retrieval**

Start with parallel or batched searches across the angles above using whatever search and browsing tools the current environment supports. Prefer source diversity over depth in the first pass.

**Step 1.5: Launch focused deep-dive tracks**

In `standard`, `deep`, and `ultradeep`, add 2-3 focused tracks such as:

- Primary-source or academic deep extraction
- Counterevidence and limitations review
- Implementation, commercial, or domain-specific validation

Each track should return structured evidence objects, not free-form notes.

**Step 2: Deepen the strongest leads**

For the most promising sources:

- Open the original page, paper, filing, documentation page, or repository
- Extract the exact claim, supporting evidence, publication/update date, and source identity
- Record enough metadata to re-check the source later
- Note any gaps or contradictions discovered during reading

**Step 3: Follow targeted tangents**

Run additional focused searches only for:

- Gaps that block synthesis
- Contradictions between high-value sources
- Claims that appear important but remain weakly sourced
- Missing stakeholder or geographic perspectives
- Gaps surfaced by deep-dive tracks or critique personas

### Evidence Object Format

Whenever possible, normalize each piece of evidence into a structure like:

```json
{
  "claim": "specific claim text",
  "evidence_quote": "exact quote or precise paraphrase from source",
  "source_url": "https://...",
  "source_title": "...",
  "published_at": "YYYY-MM-DD or unknown",
  "source_type": "academic|news|documentation|industry|government|other",
  "confidence": 0.85
}
```

This keeps synthesis manageable and reduces citation drift.

### First Finish Search (FFS) Pattern

Proceed to Phase 4 when the first quality threshold is reached:

- **Quick mode:** 10+ sources with average credibility above 60/100 or 2 minutes elapsed
- **Standard mode:** 15+ sources with average credibility above 60/100 or 5 minutes elapsed
- **Deep mode:** 25+ sources with average credibility above 70/100 or 10 minutes elapsed
- **UltraDeep mode:** 30+ sources with average credibility above 75/100 or 15 minutes elapsed

If searches are still in flight after the threshold is reached, keep the useful ones going while Phase 4 and Phase 5 begin.

### Quality Standards

**Source diversity requirements:**

- Minimum 3 source types across the report
- Temporal diversity: recent sources plus foundational older sources when relevant
- Perspective diversity: proponents, critics, and neutral analysis
- Geographic diversity when the question is global

**Credibility tracking:**

- Score each source 0-100 using `source_evaluator.py` or equivalent reasoning
- Flag low-credibility sources below 40 for extra verification
- Prioritize high-credibility sources above 80 for core claims

**Allowed techniques:**

- Web or database search available in the current environment
- Direct browsing/opening of original source pages
- Local shell and repository scripts for parsing, extraction, or validation
- Local file search for in-repo documentation
- Native runtime delegation when available
- Local orchestration helper when native delegation is unavailable

**Output:** Organized source inventory with citations, credibility scores, and identified gaps.

---

## Phase 4: TRIANGULATE - Cross-Reference Verification

**Objective:** Validate information across multiple independent sources.

**Activities:**
1. Identify claims requiring verification.
2. Cross-reference facts across 3+ sources when possible.
3. Flag contradictions or uncertainty.
4. Assess source credibility and bias.
5. Note consensus areas vs. contested areas.
6. Assign a verification status to each major claim.

**Quality standards:**
- Core claims should have 3+ independent sources.
- Clearly label single-source claims.
- Note recency where it affects reliability.
- Identify likely bias sources and conflicts of interest.

**Output:** Verified fact base with confidence levels and unresolved conflicts.

**Artifact contract:** Persist verification evidence in `phase_triangulate.json`. The helper requires non-empty `claim_checks`, explicit `verification_status` values, supporting sources for each claim, and at least one `consensus_topics` or `contested_topics` entry.

---

## Phase 4.5: OUTLINE REFINEMENT - Dynamic Evolution

**Objective:** Adapt the report structure when the evidence points somewhere different from the initial plan.

**When to execute:**
- Standard, Deep, and UltraDeep modes
- After Phase 4
- Before Phase 5

**Activities:**
1. Compare the original scope with what the evidence actually supports.
2. Identify unexpected patterns, contradictions, or emerging subtopics.
3. Promote important angles that became central during retrieval.
4. Demote sections that no longer deserve space.
5. Tighten or widen scope if the original framing proved mis-sized.
6. Run a short targeted gap-fill round if the refined outline exposes a critical missing angle.

**Quality standards:**

- Refinement must be evidence-driven, not speculative
- New sections must already have supporting evidence or an explicit gap-fill plan
- Do not drift away from the original research question without documenting why

**Output:** Revised outline aligned to the strongest evidence.

**Artifact contract:** Persist outline decisions in `phase_outline_refinement.json`. The helper requires `decision`, non-empty `evidence_driven_rationale`, `final_outline_sections`, and `gap_fill_queries` whenever `critical_gap_fill_required=true`.

---

## Phase 5: SYNTHESIZE - Insight Generation

**Objective:** Connect findings into a coherent, useful report.

**Activities:**
1. Identify patterns across sources.
2. Map relationships between concepts.
3. Generate insights that go beyond any single source.
4. Build an argument structure for the report.
5. Separate facts, interpretation, and speculation clearly.

**Output:** Synthesized narrative with evidence-backed insights and implications.

**Artifact contract:** Persist synthesis evidence in `phase_synthesize.json`. The helper requires non-empty `patterns`, `key_arguments`, and `synthesis_summary`.

---

## Phase 6: CRITIQUE - Adversarial Review

**Objective:** Pressure-test research quality before final packaging.

**Activities:**
1. Check logical consistency.
2. Verify citation completeness.
3. Identify weak evidence chains.
4. Test alternative explanations.
5. Challenge assumptions and blind spots.
6. Decide which issues require returning to retrieval or refinement.

**Mandatory personas in `deep` and `ultradeep`:**

- `Skeptical Practitioner` - Would someone doing this work daily trust the findings?
- `Adversarial Reviewer` - What would a hostile reviewer or peer reject?
- `Implementation Engineer` - Can the recommendations actually be executed?

**Critical gap loop-back:**

If any persona or critique pass identifies a critical knowledge gap, return to targeted retrieval with delta queries before moving to final packaging.

**Artifact contract:** Persist critique evidence in `phase_critique.json`. The helper requires all three personas to be marked complete, and when `critical_gap_found=true`, it also requires `delta_queries_run` to be non-empty.

**Output:** Structured critique with prioritized issues and remediation steps.

---

## Phase 7: REFINE - Gap Closure

**Objective:** Address the highest-priority weaknesses from critique.

**Activities:**
1. Run targeted follow-up retrieval.
2. Strengthen weak claims with better evidence.
3. Add missing perspectives.
4. Resolve contradictions where possible.
5. Improve clarity and structure.
6. Re-verify revised sections.

**Output:** Strengthened report with documented improvements.

**Artifact contract:** Persist refinement evidence in `phase_refine.json`. The helper requires `addressed_issues`, at least one of `follow_up_retrieval` or `strengthened_claims`, and non-empty `verification_notes`.

---

## Phase 8: PACKAGE - Report Generation

**Objective:** Deliver a professional, actionable research report.

**Activities:**
1. Structure the report with clear hierarchy.
2. Write the executive summary.
3. Develop detailed findings.
4. Add tables or diagrams only when they improve comprehension.
5. Compile a complete bibliography.
6. Add a methodology appendix.
7. Validate structure and citations before delivery.

**Output:** Completed report package in the report directory.

---

## Advanced Features

### Multi-Path Reasoning

Rather than thinking linearly, explore multiple candidate framings or hypotheses, then converge once evidence is strong enough.

### Independent Verification Rounds

Use separate retrieval passes to check whether the same claim still holds when queried from a different angle, source type, or keyword set.

### Runtime-Aware Orchestration

Treat runtime differences as an execution concern, not a reason to drop quality:

- Prefer native delegation and continuation when available
- Fall back to the local orchestration helper when native support is missing
- Report a blocker instead of silently downgrading non-negotiable capabilities

### Adaptive Depth Control

Adjust depth based on:

- Complexity of the question
- Source availability
- Stakes of the decision
- Remaining uncertainty after triangulation

### Citation Intelligence

Maintain provenance for every major claim:

- Which source supports it
- What exact evidence was used
- How credible the source is
- Whether the claim is consensus, contested, or tentative
