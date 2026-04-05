# 当前状态说明

## 定位

`deep-research` 目前是面向通用 agent 运行环境的研究型 skill。

默认交付链路为 Markdown-first：

- 主交付物是 `report.md`

该 skill 假设运行环境具备以下基础能力：

- 当前信息搜索 / 浏览能力
- 打开并检查原始来源页面的能力
- 本地 shell 与脚本执行能力
- 工作目录文件读写能力
- 原生 delegation / continuation，或允许调用本地 orchestration helper

---

## 默认输出目录

每次研究任务默认写入：

```text
./research_[YYYYMMDD]_[topic_slug]/
```

默认产物：

- `report.md`
- `sources.json`
- `run_state.json`
- `continuation_state.json`，仅在需要跨 pass 续写时保留

## Orchestration Helper

主 helper 为：

```bash
python scripts/research_engine.py --query "topic" --mode [quick|standard|deep|ultradeep] --runtime [codex|opencode|generic]
```

支持两种恢复入口：

```bash
python scripts/research_engine.py --resume ./research_[YYYYMMDD]_[topic_slug]/run_state.json --runtime [codex|opencode|generic]
python scripts/research_engine.py --resume ./research_[YYYYMMDD]_[topic_slug]/continuation_state.json --runtime [codex|opencode|generic]
```

当前 helper 的职责是：

- 创建报告目录与默认产物
- 维护 phase 结果与 section-level checkpoint
- 从现有 `report.md` 反推章节完成度
- 计算 `next_sections`
- 写出 `metadata.next_action`
- 在需要时生成或更新 `continuation_state.json`
- 从报告正文和 bibliography 自动刷新 `sources.json`
- 在最终完成前运行结构校验和 citation 校验
- 对关键 phase contract 做门禁检查
- 可选地通过 `--auto-continue` 监听 `metadata.next_action.required_files` 的变化，并在外部写入落盘后自动消费记录好的 `resume_command`

当前 helper 不是“自动写完整研究正文”的执行器；它是负责续跑、门禁、状态同步、下一步动作提示和交付一致性的编排器。

---

## Section-Level Checkpoint

`run_state.json` 当前包含：

- 当前 phase
- `phase_results`
- section checkpoint 列表
- 已完成 section
- 待完成 section
- 当前 pass 的 `next_section_ids`
- 报告字数
- validation 状态
- capability contract 状态

section checkpoint 当前覆盖的报告骨架包括：

- Executive Summary
- Introduction
- Finding 1..N
- Synthesis & Insights
- Limitations & Caveats
- Recommendations
- Bibliography
- Appendix: Methodology

helper 会在每次 `--resume` 时重新读取 `report.md`，刷新上述状态，而不是依赖内存中的旧进度。

---

## Continuation 机制

当报告未在当前 pass 内完成时：

- `run_state.json` 持续作为 durable checkpoint
- `continuation_state.json` 记录 handoff 所需的最小续写状态
- `continuation_state.json` 中包含：
  - 已完成 section
  - 当前字数
  - citation 编号状态
  - research context 摘要
  - quality metrics
  - `next_sections`

当全部 section 完成且最终门禁通过后：

- `continuation_state.json` 会被自动清理

---

## Sources Ledger

`sources.json` 当前由 helper 自动刷新，刷新依据包括：

- `## Bibliography` 中的条目
- 正文中带 `[N]` 的引用句段

当前 ledger 会记录：

- `num`
- `title`
- `url`
- `claim`
- `evidence_quote`
- `bibliography_entry`
- `supporting_snippets`
- `updated_at`

这保证了交付目录中始终存在一个和当前 `report.md` 对齐的基础 provenance ledger。

---

## Phase 1-7 Contract Gate

当前 phase 1-7 的主骨架已经进入 helper 的 contract gate。

### 全模式

- `phase_scope.json`

### `standard` / `deep` / `ultradeep`

- `phase_plan.json`
- `phase_retrieve.json`
- `phase_triangulate.json`
- `phase_outline_refinement.json`
- `phase_synthesize.json`

### `deep` / `ultradeep`

- `phase_critique.json`
- `phase_refine.json`

这些文件均写在同一报告目录下，由 helper 初始化模板，并在 `--resume` 时读取、校验、写回 contract 状态。

---

## 当前 Contract 语义

### `phase_scope.json`

要求至少包含：

- `core_components`
- `in_scope`
- `success_criteria`
- `assumptions`

### `phase_plan.json`

要求至少包含：

- `primary_source_types`
- 5 条以上 `search_queries`
- `triangulation_strategy`
- `quality_gates`

### `phase_retrieve.json`

要求至少包含：

- `broad_searches`
- 至少 2 条已完成的 `deep_dive_tracks`
- 每条已完成 deep-dive track 的 `evidence_count > 0`
- `source_inventory_summary.total_sources > 0`

### `phase_triangulate.json`

要求至少包含：

- 非空 `claim_checks`
- 每条 claim 的 `verification_status`
- 每条 claim 的 `supporting_sources`
- 至少一个 `consensus_topics` 或 `contested_topics`

### `phase_outline_refinement.json`

要求至少包含：

- `decision`
- `evidence_driven_rationale`
- `final_outline_sections`
- 若 `critical_gap_fill_required=true`，则必须有 `gap_fill_queries`

### `phase_synthesize.json`

要求至少包含：

- `patterns`
- `key_arguments`
- `synthesis_summary`

### `phase_critique.json`

要求至少包含：

- 三个 persona：
  - `Skeptical Practitioner`
  - `Adversarial Reviewer`
  - `Implementation Engineer`
- 各 persona 状态为 `completed`
- 若 `critical_gap_found=true`，则必须有 `delta_queries_run`

### `phase_refine.json`

要求至少包含：

- `addressed_issues`
- `follow_up_retrieval` 或 `strengthened_claims`
- `verification_notes`

---

## 完成门禁

报告不会仅因为 section 写完就被标记为完成。

当前完成态要求同时满足：

1. 所有 section checkpoint 已完成
2. `validate_report.py` 通过
3. `verify_citations.py` 通过
4. 当前 mode 所要求的 phase contract 全部满足

若 section 已完成但结构或引用校验失败，状态为：

- `needs_validation_fix`

若 section 已完成、校验通过，但 phase contract 未满足，状态为：

- `needs_contract_fix`

只有同时通过 validation gate 与 contract gate，最终状态才会变为：

- `completed`

---

## 当前状态机覆盖范围

当前 helper 已覆盖：

- phase 1-7 主骨架 contract 检查
- section-level 报告进度检查
- continuation handoff
- final validation gate
- sources ledger 自动刷新

当前尚未做成独立 contract artifact 的主要部分是：

- `package` phase 的单独 contract 文件

`package` 目前主要通过以下机制间接约束：

- section checkpoint
- `sources.json`
- `validate_report.py`
- `verify_citations.py`
- contract gate 的最终完成门禁

---

## 当前默认工作流结论

当前仓库的默认工作流可以概括为：

1. 在当前目录创建研究子目录
2. 用 `run_state.json` 管理 phase 与 section 状态
3. 用 `continuation_state.json` 管理跨 pass handoff
4. 用 `phase_*.json` 管理关键研究阶段的可审计 contract
5. 用 `sources.json` 维护与报告正文对齐的引用 ledger
6. 只有在 section、validation、contract 三类门禁全部通过后，报告才会被标记为完成
