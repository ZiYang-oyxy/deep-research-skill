#!/usr/bin/env python3
"""
Deep Research Engine
Orchestrates comprehensive research across multiple sources with verification,
section-level checkpoints, and continuation state management.
"""

import argparse
import builtins
import json
import re
import shlex
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from report_contract import (
    REPORT_SECTION_SPECS,
    SECTION_PATTERNS_BY_ID,
    count_length_units,
    get_any_finding_pattern,
    get_default_finding_heading,
    get_default_section_heading,
    get_default_section_title,
    get_finding_pattern,
    min_length_for_section,
    resolve_section_id,
)


def print(*args, **kwargs):
    """Force line-buffer-like behavior even when stdout/stderr are piped."""
    kwargs.setdefault("flush", True)
    return builtins.print(*args, **kwargs)


class ResearchPhase(Enum):
    """Research pipeline phases."""
    SCOPE = "scope"
    PLAN = "plan"
    RETRIEVE = "retrieve"
    TRIANGULATE = "triangulate"
    OUTLINE_REFINEMENT = "outline_refinement"
    SYNTHESIZE = "synthesize"
    CRITIQUE = "critique"
    REFINE = "refine"
    PACKAGE = "package"


class ResearchMode(Enum):
    """Research depth modes."""
    QUICK = "quick"
    STANDARD = "standard"
    DEEP = "deep"
    ULTRADEEP = "ultradeep"


class RuntimeAdapter(Enum):
    """Runtime adapters for environment-specific orchestration guidance."""
    GENERIC = "generic"
    CODEX = "codex"
    OPENCODE = "opencode"


class WriteMode(Enum):
    """Report writing modes exposed by the helper CLI."""
    SKELETON_ONLY = "skeleton_only"
    ATTEMPT_AUTOWRITE = "attempt_autowrite"


STATE_VERSION = "2.2.0"
AUTO_CONTINUE_HEARTBEAT_SECONDS = 5.0


DEFAULT_PASS_WORD_BUDGET = {
    ResearchMode.QUICK: 4000,
    ResearchMode.STANDARD: 6500,
    ResearchMode.DEEP: 7500,
    ResearchMode.ULTRADEEP: 9000,
}

SECTION_TARGETS = {
    ResearchMode.QUICK: {
        "executive_summary": 300,
        "introduction": 500,
        "finding": 700,
        "synthesis": 600,
        "limitations": 350,
        "recommendations": 350,
        "bibliography": 250,
        "methodology": 350,
    },
    ResearchMode.STANDARD: {
        "executive_summary": 300,
        "introduction": 650,
        "finding": 900,
        "synthesis": 900,
        "limitations": 500,
        "recommendations": 500,
        "bibliography": 300,
        "methodology": 500,
    },
    ResearchMode.DEEP: {
        "executive_summary": 350,
        "introduction": 800,
        "finding": 1400,
        "synthesis": 1200,
        "limitations": 700,
        "recommendations": 700,
        "bibliography": 350,
        "methodology": 700,
    },
    ResearchMode.ULTRADEEP: {
        "executive_summary": 400,
        "introduction": 900,
        "finding": 1800,
        "synthesis": 1500,
        "limitations": 900,
        "recommendations": 900,
        "bibliography": 400,
        "methodology": 900,
    },
}

SECTION_MIN_WORDS = {
    "executive_summary": 80,
    "introduction": 120,
    "finding": 120,
    "synthesis": 100,
    "limitations": 80,
    "recommendations": 60,
    "bibliography": 1,
    "methodology": 80,
}


@dataclass
class Source:
    """Represents a research source."""

    url: str
    title: str
    snippet: str
    retrieved_at: str
    credibility_score: float = 0.0
    source_type: str = "web"
    verification_status: str = "unverified"

    def to_citation(self, index: int) -> str:
        """Generate citation string."""
        return f"[{index}] {self.title} - {self.url} (Retrieved: {self.retrieved_at})"


@dataclass
class SectionCheckpoint:
    """Tracks the completion status of one report section."""

    section_id: str
    title: str
    section_type: str
    heading: str
    target_words: int
    status: str = "pending"
    actual_words: int = 0
    citations_used: List[int] = field(default_factory=list)
    summary: str = ""
    started_at: Optional[str] = None
    completed_at: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SectionCheckpoint":
        """Load a checkpoint from serialized data."""
        return cls(
            section_id=data["section_id"],
            title=data["title"],
            section_type=data["section_type"],
            heading=data["heading"],
            target_words=int(data.get("target_words", 0)),
            status=data.get("status", "pending"),
            actual_words=int(data.get("actual_words", 0)),
            citations_used=[int(item) for item in data.get("citations_used", [])],
            summary=data.get("summary", ""),
            started_at=data.get("started_at"),
            completed_at=data.get("completed_at"),
        )

    def to_continuation_payload(self) -> Dict[str, Any]:
        """Serialize the checkpoint for continuation handoff."""
        return {
            "id": self.section_id,
            "type": self.section_type,
            "title": self.title,
            "target_words": self.target_words,
            "heading": self.heading,
            "status": self.status,
        }


@dataclass
class ContinuationState:
    """Represents the active continuation handoff state."""

    version: str
    report_id: str
    file_path: str
    mode: str
    progress: Dict[str, Any]
    citations: Dict[str, Any]
    research_context: Dict[str, Any]
    quality_metrics: Dict[str, Any]
    next_sections: List[Dict[str, Any]]
    runtime: str = "generic"
    run_state_path: Optional[str] = None
    generated_at: Optional[str] = None

    def save(self, filepath: Path):
        """Persist continuation state to disk."""
        with open(filepath, "w", encoding="utf-8") as handle:
            json.dump(asdict(self), handle, indent=2)

    @classmethod
    def load(cls, filepath: Path) -> "ContinuationState":
        """Load continuation state from disk."""
        with open(filepath, "r", encoding="utf-8") as handle:
            data = json.load(handle)

        return cls(
            version=data.get("version", STATE_VERSION),
            report_id=data.get("report_id", ""),
            file_path=data["file_path"],
            mode=data["mode"],
            progress=data.get("progress", {}),
            citations=data.get("citations", {}),
            research_context=data.get("research_context", {}),
            quality_metrics=data.get("quality_metrics", {}),
            next_sections=data.get("next_sections", []),
            runtime=data.get("runtime", "generic"),
            run_state_path=data.get("run_state_path"),
            generated_at=data.get("generated_at"),
        )


@dataclass
class ResearchState:
    """Maintains research state across phases and report assembly."""

    query: str
    mode: ResearchMode
    phase: ResearchPhase
    scope: Dict[str, Any]
    plan: Dict[str, Any]
    sources: List[Source]
    findings: List[Dict[str, Any]]
    synthesis: Dict[str, Any]
    critique: Dict[str, Any]
    report: str
    metadata: Dict[str, Any]
    section_checkpoints: List[SectionCheckpoint] = field(default_factory=list)
    phase_results: Dict[str, Any] = field(default_factory=dict)
    status: str = "initialized"

    def save(self, filepath: Path):
        """Save research state to file with retry logic."""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                with open(filepath, "w", encoding="utf-8") as handle:
                    json.dump(self._serialize(), handle, indent=2)
                return
            except (IOError, OSError) as exc:
                if attempt == max_retries - 1:
                    raise IOError(
                        f"Failed to save state after {max_retries} attempts: {exc}"
                    ) from exc
                time.sleep((attempt + 1) * 0.5)

    def _serialize(self) -> Dict[str, Any]:
        """Convert to a serializable dictionary."""
        return {
            "query": self.query,
            "mode": self.mode.value,
            "phase": self.phase.value,
            "scope": self.scope,
            "plan": self.plan,
            "sources": [asdict(source) for source in self.sources],
            "findings": self.findings,
            "synthesis": self.synthesis,
            "critique": self.critique,
            "report": self.report,
            "metadata": self.metadata,
            "section_checkpoints": [asdict(item) for item in self.section_checkpoints],
            "phase_results": self.phase_results,
            "status": self.status,
        }

    @classmethod
    def load(cls, filepath: Path) -> "ResearchState":
        """Load research state from disk."""
        with open(filepath, "r", encoding="utf-8") as handle:
            data = json.load(handle)

        return cls(
            query=data["query"],
            mode=ResearchMode(data["mode"]),
            phase=ResearchPhase(data["phase"]),
            scope=data.get("scope", {}),
            plan=data.get("plan", {}),
            sources=[Source(**item) for item in data.get("sources", [])],
            findings=data.get("findings", []),
            synthesis=data.get("synthesis", {}),
            critique=data.get("critique", {}),
            report=data.get("report", ""),
            metadata=data.get("metadata", {}),
            section_checkpoints=[
                SectionCheckpoint.from_dict(item)
                for item in data.get("section_checkpoints", [])
            ],
            phase_results=data.get("phase_results", {}),
            status=data.get("status", "initialized"),
        )


class ResearchEngine:
    """Main research orchestration engine."""

    def __init__(
        self,
        mode: ResearchMode = ResearchMode.STANDARD,
        runtime: RuntimeAdapter = RuntimeAdapter.GENERIC,
        pass_word_budget: Optional[int] = None,
        write_mode: WriteMode = WriteMode.SKELETON_ONLY,
    ):
        self.mode = mode
        self.runtime = runtime
        self.write_mode = write_mode
        self.state: Optional[ResearchState] = None
        self.output_root = Path.cwd()
        self.output_dir: Optional[Path] = None
        self.pass_word_budget = pass_word_budget or DEFAULT_PASS_WORD_BUDGET[mode]
        self._resume_source: Optional[str] = None
        self._scripts_dir = Path(__file__).resolve().parent

    def _slugify(self, value: str, max_length: int = 48) -> str:
        """Create a filesystem-safe slug for report directories."""
        slug = re.sub(r"[^a-zA-Z0-9]+", "_", value.strip().lower()).strip("_")
        if not slug:
            slug = "research_topic"
        return slug[:max_length].rstrip("_")

    def _prepare_output_dir(self, query: str) -> Path:
        """Create the report directory for the current run."""
        date_part = datetime.now().strftime("%Y%m%d")
        slug = self._slugify(query)
        output_dir = self.output_root / f"research_{date_part}_{slug}"
        output_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir = output_dir
        return output_dir

    def _get_report_path(self, output_dir: Optional[Path] = None) -> Path:
        """Return the main report path."""
        return self._get_output_dir(output_dir) / "report.md"

    def _get_sources_path(self, output_dir: Optional[Path] = None) -> Path:
        """Return the sources ledger path."""
        return self._get_output_dir(output_dir) / "sources.json"

    def _get_run_state_path(self, output_dir: Optional[Path] = None) -> Path:
        """Return the durable checkpoint path."""
        return self._get_output_dir(output_dir) / "run_state.json"

    def _get_continuation_state_path(self, output_dir: Optional[Path] = None) -> Path:
        """Return the active continuation handoff path."""
        return self._get_output_dir(output_dir) / "continuation_state.json"

    def _get_phase_artifact_path(
        self,
        phase: ResearchPhase,
        output_dir: Optional[Path] = None,
    ) -> Path:
        """Return the artifact file path for a phase contract."""
        return self._get_output_dir(output_dir) / f"phase_{phase.value}.json"

    def _get_output_dir(self, output_dir: Optional[Path] = None) -> Path:
        """Resolve the active output directory."""
        if output_dir is not None:
            return output_dir
        if self.output_dir is None:
            raise ValueError("Output directory is not initialized")
        return self.output_dir

    def _get_runtime_reference(self) -> str:
        """Return the runtime adapter reference file."""
        if self.runtime == RuntimeAdapter.CODEX:
            return "reference/runtime-codex.md"
        if self.runtime == RuntimeAdapter.OPENCODE:
            return "reference/runtime-opencode.md"
        return "reference/methodology.md"

    def _required_contract_phases(self) -> List[ResearchPhase]:
        """Return phases that have non-silent degradation contracts."""
        phases = [ResearchPhase.SCOPE]
        if self.mode in (
            ResearchMode.STANDARD,
            ResearchMode.DEEP,
            ResearchMode.ULTRADEEP,
        ):
            phases.extend(
                [
                    ResearchPhase.PLAN,
                    ResearchPhase.RETRIEVE,
                    ResearchPhase.TRIANGULATE,
                    ResearchPhase.OUTLINE_REFINEMENT,
                    ResearchPhase.SYNTHESIZE,
                ]
            )
        if self.mode in (ResearchMode.DEEP, ResearchMode.ULTRADEEP):
            phases.extend([ResearchPhase.CRITIQUE, ResearchPhase.REFINE])
        return phases

    def _default_phase_artifact(self, phase: ResearchPhase) -> Dict[str, Any]:
        """Build a default artifact template for a phase."""
        base = {
            "phase": phase.value,
            "status": "pending",
            "updated_at": None,
            "notes": [],
            "blocking_reason": "",
        }

        if phase == ResearchPhase.SCOPE:
            base.update(
                {
                    "core_components": [],
                    "stakeholder_perspectives": [],
                    "in_scope": [],
                    "out_of_scope": [],
                    "success_criteria": [],
                    "assumptions": [],
                }
            )
        elif phase == ResearchPhase.PLAN:
            base.update(
                {
                    "primary_source_types": [],
                    "secondary_source_types": [],
                    "knowledge_dependencies": [],
                    "search_queries": [],
                    "triangulation_strategy": [],
                    "quality_gates": [],
                }
            )
        elif phase == ResearchPhase.RETRIEVE:
            base.update(
                {
                    "broad_searches": [],
                    "deep_dive_tracks": [
                        {
                            "name": "primary_source_extraction",
                            "focus": "Primary-source or academic extraction",
                            "status": "pending",
                            "evidence_count": 0,
                            "notes": [],
                        },
                        {
                            "name": "counterevidence_review",
                            "focus": "Counterevidence and limitations review",
                            "status": "pending",
                            "evidence_count": 0,
                            "notes": [],
                        },
                        {
                            "name": "implementation_validation",
                            "focus": "Implementation, commercial, or domain-specific validation",
                            "status": "pending",
                            "evidence_count": 0,
                            "notes": [],
                        },
                    ],
                    "source_inventory_summary": {
                        "total_sources": 0,
                        "source_types": [],
                        "coverage_notes": [],
                    },
                }
            )
        elif phase == ResearchPhase.TRIANGULATE:
            base.update(
                {
                    "claim_checks": [],
                    "consensus_topics": [],
                    "contested_topics": [],
                    "unresolved_gaps": [],
                }
            )
        elif phase == ResearchPhase.OUTLINE_REFINEMENT:
            base.update(
                {
                    "decision": "pending",
                    "initial_outline_summary": [],
                    "evidence_driven_rationale": [],
                    "outline_changes": [],
                    "critical_gap_fill_required": False,
                    "gap_fill_queries": [],
                    "final_outline_sections": [],
                }
            )
        elif phase == ResearchPhase.SYNTHESIZE:
            base.update(
                {
                    "patterns": [],
                    "concept_relationships": [],
                    "novel_insights": [],
                    "frameworks": [],
                    "key_arguments": [],
                    "synthesis_summary": [],
                }
            )
        elif phase == ResearchPhase.CRITIQUE:
            base.update(
                {
                    "personas": [
                        {
                            "name": "Skeptical Practitioner",
                            "status": "pending",
                            "key_objections": [],
                            "critical_gaps": [],
                            "resolution_notes": [],
                        },
                        {
                            "name": "Adversarial Reviewer",
                            "status": "pending",
                            "key_objections": [],
                            "critical_gaps": [],
                            "resolution_notes": [],
                        },
                        {
                            "name": "Implementation Engineer",
                            "status": "pending",
                            "key_objections": [],
                            "critical_gaps": [],
                            "resolution_notes": [],
                        },
                    ],
                    "critical_gap_found": False,
                    "delta_queries_run": [],
                    "resolution_summary": [],
                }
            )
        elif phase == ResearchPhase.REFINE:
            base.update(
                {
                    "addressed_issues": [],
                    "follow_up_retrieval": [],
                    "strengthened_claims": [],
                    "remaining_limitations": [],
                    "verification_notes": [],
                }
            )
        return base

    def _initialize_phase_artifacts(self):
        """Create contract artifact templates for required phases."""
        if self.state is None:
            return

        artifact_paths = {}
        for phase in self._required_contract_phases():
            artifact_path = self._get_phase_artifact_path(phase)
            artifact_paths[phase.value] = str(artifact_path)
            if artifact_path.exists():
                continue
            artifact_path.write_text(
                json.dumps(self._default_phase_artifact(phase), indent=2) + "\n",
                encoding="utf-8",
            )

        if artifact_paths:
            self.state.metadata["phase_artifact_paths"] = artifact_paths

    def _build_section_plan(self) -> List[SectionCheckpoint]:
        """Create the default section checkpoint plan."""
        targets = SECTION_TARGETS[self.mode]
        checkpoints = [
            self._make_checkpoint(
                "executive_summary",
                get_default_section_title("executive_summary"),
                "executive_summary",
                get_default_section_heading("executive_summary"),
                targets["executive_summary"],
            ),
            self._make_checkpoint(
                "introduction",
                get_default_section_title("introduction"),
                "introduction",
                get_default_section_heading("introduction"),
                targets["introduction"],
            ),
        ]

        for index in range(1, 5):
            checkpoints.append(
                self._make_checkpoint(
                    f"finding_{index}",
                    f"发现 {index}",
                    "finding",
                    get_default_finding_heading(index),
                    targets["finding"],
                )
            )

        checkpoints.extend(
            [
                self._make_checkpoint(
                    "synthesis_insights",
                    get_default_section_title("synthesis_insights"),
                    "synthesis",
                    get_default_section_heading("synthesis_insights"),
                    targets["synthesis"],
                ),
                self._make_checkpoint(
                    "limitations_caveats",
                    get_default_section_title("limitations_caveats"),
                    "limitations",
                    get_default_section_heading("limitations_caveats"),
                    targets["limitations"],
                ),
                self._make_checkpoint(
                    "recommendations",
                    get_default_section_title("recommendations"),
                    "recommendations",
                    get_default_section_heading("recommendations"),
                    targets["recommendations"],
                ),
                self._make_checkpoint(
                    "bibliography",
                    get_default_section_title("bibliography"),
                    "bibliography",
                    get_default_section_heading("bibliography"),
                    targets["bibliography"],
                ),
                self._make_checkpoint(
                    "methodology_appendix",
                    get_default_section_title("methodology_appendix"),
                    "methodology",
                    get_default_section_heading("methodology_appendix"),
                    targets["methodology"],
                ),
            ]
        )
        return checkpoints

    def _make_checkpoint(
        self,
        section_id: str,
        title: str,
        section_type: str,
        heading: str,
        target_words: int,
    ) -> SectionCheckpoint:
        """Convenience builder for section checkpoints."""
        return SectionCheckpoint(
            section_id=section_id,
            title=title,
            section_type=section_type,
            heading=heading,
            target_words=target_words,
        )

    def initialize_research(self, query: str) -> ResearchState:
        """Initialize a new research session."""
        output_dir = self._prepare_output_dir(query)
        report_path = self._get_report_path(output_dir)
        sources_path = self._get_sources_path(output_dir)
        run_state_path = self._get_run_state_path(output_dir)
        report_path.touch(exist_ok=True)
        if not sources_path.exists():
            sources_path.write_text("[]\n", encoding="utf-8")

        report_id = output_dir.name
        self.state = ResearchState(
            query=query,
            mode=self.mode,
            phase=ResearchPhase.SCOPE,
            scope={},
            plan={},
            sources=[],
            findings=[],
            synthesis={},
            critique={},
            report="",
            metadata={
                "started_at": datetime.now().isoformat(),
                "version": STATE_VERSION,
                "report_id": report_id,
                "runtime": self.runtime.value,
                "write_mode": self.write_mode.value,
                "output_dir": str(output_dir),
                "report_path": str(report_path),
                "sources_path": str(sources_path),
                "run_state_path": str(run_state_path),
                "continuation_state_path": str(
                    self._get_continuation_state_path(output_dir)
                ),
                "pass_word_budget": self.pass_word_budget,
                "continuation_count": 0,
                "resume_history": [],
                "next_action": {},
            },
            section_checkpoints=self._build_section_plan(),
            phase_results={},
            status="initialized",
        )
        self._initialize_phase_artifacts()
        self.refresh_state_from_artifacts()
        return self.state

    def load_resume_state(self, state_file: Path) -> str:
        """Load either run_state.json or continuation_state.json."""
        with open(state_file, "r", encoding="utf-8") as handle:
            payload = json.load(handle)

        if "query" in payload and "phase" in payload:
            self.state = ResearchState.load(state_file)
            self.output_dir = state_file.parent
            self._resume_source = "run_state"
            return "run_state"

        continuation_state = ContinuationState.load(state_file)
        run_state_path = (
            Path(continuation_state.run_state_path)
            if continuation_state.run_state_path
            else state_file.with_name("run_state.json")
        )
        if not run_state_path.exists():
            raise FileNotFoundError(
                "Continuation state does not have a matching run_state.json"
            )

        self.state = ResearchState.load(run_state_path)
        self.output_dir = run_state_path.parent
        self._resume_source = "continuation_state"
        self.state.metadata["resume_source"] = str(state_file)
        self.state.metadata["continuation_count"] = int(
            self.state.metadata.get("continuation_count", 0)
        ) + 1
        history = list(self.state.metadata.get("resume_history", []))
        history.append(
            {
                "resumed_at": datetime.now().isoformat(),
                "source": str(state_file),
            }
        )
        self.state.metadata["resume_history"] = history
        return "continuation_state"

    def _bootstrap_loaded_state(self):
        """Ensure a loaded state has the new metadata and artifact structure."""
        if self.state is None:
            raise ValueError("Research state is not initialized")

        if self.output_dir is None:
            output_dir_value = self.state.metadata.get("output_dir")
            self.output_dir = Path(output_dir_value) if output_dir_value else Path.cwd()

        self.output_dir.mkdir(parents=True, exist_ok=True)
        report_path = self._get_report_path()
        sources_path = self._get_sources_path()
        report_path.touch(exist_ok=True)
        if not sources_path.exists():
            sources_path.write_text("[]\n", encoding="utf-8")

        self.state.metadata.setdefault("version", STATE_VERSION)
        self.state.metadata.setdefault("report_id", self.output_dir.name)
        self.state.metadata["runtime"] = self.runtime.value
        self.state.metadata.setdefault("write_mode", self.write_mode.value)
        self.state.metadata["output_dir"] = str(self.output_dir)
        self.state.metadata["report_path"] = str(report_path)
        self.state.metadata["sources_path"] = str(sources_path)
        self.state.metadata["run_state_path"] = str(self._get_run_state_path())
        self.state.metadata["continuation_state_path"] = str(
            self._get_continuation_state_path()
        )
        self.state.metadata["pass_word_budget"] = self.pass_word_budget
        self.state.metadata.setdefault("continuation_count", 0)
        self.state.metadata.setdefault("resume_history", [])
        self.state.metadata.setdefault("phase_artifact_paths", {})
        self.state.metadata.setdefault("next_action", {})

        if not self.state.section_checkpoints:
            self.state.section_checkpoints = self._build_section_plan()

        if not self.state.phase_results:
            self.state.phase_results = {}

        self._initialize_phase_artifacts()

    def _count_words(self, text: str) -> int:
        """Count cross-language length units in a text block."""
        return count_length_units(text)

    def _write_mode_summary(self) -> str:
        """Return a concise description of the helper's writing behavior."""
        if self.write_mode == WriteMode.ATTEMPT_AUTOWRITE:
            return (
                "Automatic writing mode requested. This helper still mainly initializes "
                "phase artifacts, state files, and the report skeleton; actual retrieval, "
                "analysis, and prose generation usually require the agent runtime or delegated subagents."
            )
        return (
            "Skeleton-only mode. This run initializes phase artifacts, state files, "
            "and the report skeleton only."
        )

    def _print_post_run_guidance(self):
        """Print direct guidance about what the helper has and has not completed."""
        if self.state is None:
            return

        print("Status note:")
        print(f"  - {self._write_mode_summary()}")
        if self.state.status == "completed":
            print("  - Final body content is present and validation passed.")
            return

        print("  - Current run only initialized research artifacts; report body text has not been fully generated yet.")
        next_action = self.state.metadata.get("next_action", {})
        if next_action.get("kind") == "write_sections":
            required_sections = next_action.get("required_section_ids", [])
            if required_sections:
                print("  - Remaining sections: " + ", ".join(required_sections))
        resume_command = next_action.get("resume_command")
        if resume_command:
            print(f"  - Resume after edits: {resume_command}")

    def _load_sources_ledger(self) -> List[Dict[str, Any]]:
        """Read sources.json without crashing on malformed content."""
        sources_path = self._get_sources_path()
        if not sources_path.exists():
            return []

        try:
            payload = json.loads(sources_path.read_text(encoding="utf-8") or "[]")
        except json.JSONDecodeError as exc:
            print(
                f"Warning: sources ledger is not valid JSON and will be ignored: {exc}",
                file=sys.stderr,
            )
            return []

        if isinstance(payload, list):
            return payload

        print(
            "Warning: sources ledger is not a JSON array and will be ignored",
            file=sys.stderr,
        )
        return []

    def _parse_bibliography_entries(self, report_content: str) -> List[Dict[str, Any]]:
        """Parse bibliography entries from the report."""
        result = self._extract_top_level_section(
            report_content,
            list(SECTION_PATTERNS_BY_ID["bibliography"]),
        )
        if not result:
            return []

        _, body = result
        entries: List[Dict[str, Any]] = []
        current_entry: Optional[Dict[str, Any]] = None

        for raw_line in body.splitlines():
            line = raw_line.strip()
            if not line:
                continue

            match_num = re.match(r"^\[(\d+)\]\s+(.+)$", line)
            if match_num:
                if current_entry is not None:
                    entries.append(current_entry)

                rest = match_num.group(2)
                current_entry = {
                    "num": int(match_num.group(1)),
                    "raw": line,
                    "title": None,
                    "url": None,
                }
                title_match = re.search(r'"([^"]+)"', rest)
                if title_match:
                    current_entry["title"] = title_match.group(1).strip()
                else:
                    title_text = re.sub(r"https?://\S+", "", rest).strip()
                    current_entry["title"] = title_text or f"Source {match_num.group(1)}"

                url_match = re.search(r"https?://[^\s\)]+", rest)
                if url_match:
                    current_entry["url"] = url_match.group(0)
            elif current_entry is not None:
                current_entry["raw"] += " " + line
                if current_entry.get("url") is None:
                    url_match = re.search(r"https?://[^\s\)]+", line)
                    if url_match:
                        current_entry["url"] = url_match.group(0)

        if current_entry is not None:
            entries.append(current_entry)

        return entries

    def _extract_claim_snippets(self, report_content: str) -> Dict[int, List[str]]:
        """Collect sentence-level snippets keyed by citation number."""
        body = report_content
        bibliography_match = None
        for pattern in SECTION_PATTERNS_BY_ID["bibliography"]:
            bibliography_match = re.search(
                pattern,
                report_content,
                re.MULTILINE | re.IGNORECASE,
            )
            if bibliography_match:
                break
        if bibliography_match:
            body = report_content[:bibliography_match.start()]

        snippets: Dict[int, List[str]] = {}
        normalized = body.replace("\n", " ")
        segments = re.split(r"(?<=[\.\!\?])\s+", normalized)

        for segment in segments:
            cleaned = " ".join(segment.split()).strip()
            if not cleaned:
                continue
            for citation_num in {
                int(item) for item in re.findall(r"\[(\d+)\]", cleaned)
            }:
                snippets.setdefault(citation_num, [])
                if cleaned not in snippets[citation_num]:
                    snippets[citation_num].append(cleaned)

        return snippets

    def _sync_sources_from_report(self, report_content: str):
        """Refresh sources.json from bibliography and cited snippets."""
        if self.state is None:
            return

        bibliography_entries = self._parse_bibliography_entries(report_content)
        snippet_map = self._extract_claim_snippets(report_content)
        existing_entries = {
            int(item["num"]): item
            for item in self._load_sources_ledger()
            if item.get("num") is not None
        }

        refreshed_entries: List[Dict[str, Any]] = []
        refreshed_sources: List[Source] = []

        for entry in bibliography_entries:
            num = entry["num"]
            existing = dict(existing_entries.get(num, {}))
            snippets = snippet_map.get(num, [])
            claim = snippets[0] if snippets else existing.get("claim", "")
            evidence_quote = snippets[1] if len(snippets) > 1 else claim

            refreshed = {
                "num": num,
                "title": entry.get("title") or existing.get("title") or f"Source {num}",
                "url": entry.get("url") or existing.get("url") or "",
                "claim": claim,
                "evidence_quote": evidence_quote,
                "bibliography_entry": entry["raw"],
                "supporting_snippets": snippets[:3],
                "updated_at": datetime.now().isoformat(),
            }

            for key, value in existing.items():
                refreshed.setdefault(key, value)

            refreshed_entries.append(refreshed)
            refreshed_sources.append(
                Source(
                    url=refreshed["url"],
                    title=refreshed["title"],
                    snippet=refreshed["claim"] or refreshed["evidence_quote"],
                    retrieved_at=refreshed["updated_at"],
                    credibility_score=float(existing.get("credibility_score", 0.0)),
                    source_type=existing.get("source_type", "report_bibliography"),
                    verification_status=existing.get("verification_status", "unverified"),
                )
            )

        self._get_sources_path().write_text(
            json.dumps(refreshed_entries, indent=2) + "\n",
            encoding="utf-8",
        )
        self.state.sources = refreshed_sources

    def _load_phase_artifact(self, phase: ResearchPhase) -> Tuple[Optional[Dict[str, Any]], List[str]]:
        """Load a phase artifact and return schema-level issues."""
        artifact_path = self._get_phase_artifact_path(phase)
        if not artifact_path.exists():
            return None, [f"Missing artifact file: {artifact_path.name}"]

        try:
            payload = json.loads(artifact_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            return None, [f"Invalid JSON in {artifact_path.name}: {exc}"]

        issues = []
        if payload.get("phase") != phase.value:
            issues.append(
                f"{artifact_path.name} has phase={payload.get('phase')!r}, expected {phase.value!r}"
            )
        return payload, issues

    def _evaluate_retrieve_contract(self, artifact: Dict[str, Any], issues: List[str]) -> List[str]:
        """Validate the retrieve contract artifact."""
        if artifact.get("status") != "completed":
            issues.append("Retrieve artifact status must be 'completed'")

        broad_searches = artifact.get("broad_searches", [])
        if not broad_searches:
            issues.append("Retrieve artifact must record broad_searches")

        deep_dive_tracks = artifact.get("deep_dive_tracks", [])
        completed_tracks = [
            track
            for track in deep_dive_tracks
            if track.get("status") == "completed"
        ]
        if len(completed_tracks) < 2:
            issues.append("Retrieve artifact must include at least 2 completed deep_dive_tracks")

        for track in completed_tracks:
            if int(track.get("evidence_count", 0)) <= 0:
                issues.append(
                    f"Deep-dive track {track.get('name', '<unknown>')} must record evidence_count > 0"
                )

        summary = artifact.get("source_inventory_summary", {})
        if int(summary.get("total_sources", 0)) <= 0:
            issues.append("Retrieve artifact must record source_inventory_summary.total_sources > 0")

        return issues

    def _evaluate_scope_contract(self, artifact: Dict[str, Any], issues: List[str]) -> List[str]:
        """Validate the scope contract artifact."""
        if artifact.get("status") != "completed":
            issues.append("Scope artifact status must be 'completed'")

        if not artifact.get("core_components"):
            issues.append("Scope artifact must include core_components")
        if not artifact.get("in_scope"):
            issues.append("Scope artifact must include in_scope")
        if not artifact.get("success_criteria"):
            issues.append("Scope artifact must include success_criteria")
        if not artifact.get("assumptions"):
            issues.append("Scope artifact must include assumptions")

        return issues

    def _evaluate_plan_contract(self, artifact: Dict[str, Any], issues: List[str]) -> List[str]:
        """Validate the plan contract artifact."""
        if artifact.get("status") != "completed":
            issues.append("Plan artifact status must be 'completed'")

        if not artifact.get("primary_source_types"):
            issues.append("Plan artifact must include primary_source_types")
        if not artifact.get("search_queries"):
            issues.append("Plan artifact must include search_queries")
        elif len(artifact.get("search_queries", [])) < 5:
            issues.append("Plan artifact should record at least 5 search_queries")

        if not artifact.get("triangulation_strategy"):
            issues.append("Plan artifact must include triangulation_strategy")
        if not artifact.get("quality_gates"):
            issues.append("Plan artifact must include quality_gates")

        return issues

    def _evaluate_triangulate_contract(self, artifact: Dict[str, Any], issues: List[str]) -> List[str]:
        """Validate the triangulate contract artifact."""
        if artifact.get("status") != "completed":
            issues.append("Triangulate artifact status must be 'completed'")

        claim_checks = artifact.get("claim_checks", [])
        if not claim_checks:
            issues.append("Triangulate artifact must include claim_checks")
            return issues

        for index, claim_check in enumerate(claim_checks, start=1):
            claim = claim_check.get("claim")
            if not claim:
                issues.append(f"Triangulate claim_checks[{index}] is missing claim text")
            if not claim_check.get("verification_status"):
                issues.append(
                    f"Triangulate claim_checks[{index}] must include verification_status"
                )
            supporting_sources = claim_check.get("supporting_sources", [])
            if not supporting_sources:
                issues.append(
                    f"Triangulate claim_checks[{index}] must include supporting_sources"
                )

        if not artifact.get("consensus_topics") and not artifact.get("contested_topics"):
            issues.append(
                "Triangulate artifact must record at least one consensus_topics or contested_topics entry"
            )

        return issues

    def _evaluate_outline_refinement_contract(
        self,
        artifact: Dict[str, Any],
        issues: List[str],
    ) -> List[str]:
        """Validate the outline refinement contract artifact."""
        if artifact.get("status") != "completed":
            issues.append("Outline refinement artifact status must be 'completed'")

        decision = artifact.get("decision")
        if decision not in {"kept", "refined"}:
            issues.append("Outline refinement artifact decision must be 'kept' or 'refined'")

        if not artifact.get("evidence_driven_rationale"):
            issues.append(
                "Outline refinement artifact must include evidence_driven_rationale"
            )

        if decision == "refined" and not artifact.get("outline_changes"):
            issues.append(
                "Outline refinement artifact with decision='refined' must include outline_changes"
            )

        if not artifact.get("final_outline_sections"):
            issues.append(
                "Outline refinement artifact must include final_outline_sections"
            )
        else:
            outline_sections = {str(item) for item in artifact.get("final_outline_sections", [])}
            outline_section_ids = {
                section_id
                for item in outline_sections
                for section_id in [resolve_section_id(item)]
                if section_id is not None
            }
            missing_sections = [
                str(spec["title"])
                for spec in REPORT_SECTION_SPECS
                if str(spec["id"]) not in outline_section_ids
            ]
            if missing_sections:
                issues.append(
                    "Outline refinement artifact is missing final_outline_sections entries: "
                    + ", ".join(missing_sections)
                )

        if artifact.get("critical_gap_fill_required") and not artifact.get("gap_fill_queries"):
            issues.append(
                "Outline refinement artifact must include gap_fill_queries when critical_gap_fill_required=true"
            )

        return issues

    def _evaluate_synthesize_contract(self, artifact: Dict[str, Any], issues: List[str]) -> List[str]:
        """Validate the synthesize contract artifact."""
        if artifact.get("status") != "completed":
            issues.append("Synthesize artifact status must be 'completed'")

        if not artifact.get("patterns"):
            issues.append("Synthesize artifact must include patterns")
        if not artifact.get("key_arguments"):
            issues.append("Synthesize artifact must include key_arguments")
        if not artifact.get("synthesis_summary"):
            issues.append("Synthesize artifact must include synthesis_summary")

        return issues

    def _evaluate_critique_contract(self, artifact: Dict[str, Any], issues: List[str]) -> List[str]:
        """Validate the critique contract artifact."""
        if artifact.get("status") != "completed":
            issues.append("Critique artifact status must be 'completed'")

        personas = artifact.get("personas", [])
        required_personas = {
            "Skeptical Practitioner",
            "Adversarial Reviewer",
            "Implementation Engineer",
        }
        persona_map = {
            str(item.get("name")): item
            for item in personas
            if item.get("name")
        }

        missing_personas = sorted(required_personas - set(persona_map))
        if missing_personas:
            issues.append(
                "Critique artifact is missing personas: " + ", ".join(missing_personas)
            )

        for name in required_personas & set(persona_map):
            persona = persona_map[name]
            if persona.get("status") != "completed":
                issues.append(f"Persona {name} must have status='completed'")

        critical_gap_found = bool(artifact.get("critical_gap_found"))
        delta_queries_run = artifact.get("delta_queries_run", [])

        any_persona_gap = any(persona.get("critical_gaps") for persona in personas)
        if any_persona_gap and not critical_gap_found:
            issues.append(
                "Critique artifact must set critical_gap_found=true when personas record critical_gaps"
            )

        if critical_gap_found and not delta_queries_run:
            issues.append(
                "Critique artifact must record delta_queries_run when critical_gap_found=true"
            )

        return issues

    def _evaluate_refine_contract(self, artifact: Dict[str, Any], issues: List[str]) -> List[str]:
        """Validate the refine contract artifact."""
        if artifact.get("status") != "completed":
            issues.append("Refine artifact status must be 'completed'")

        if not artifact.get("addressed_issues"):
            issues.append("Refine artifact must include addressed_issues")

        if not artifact.get("follow_up_retrieval") and not artifact.get("strengthened_claims"):
            issues.append(
                "Refine artifact must include follow_up_retrieval or strengthened_claims"
            )

        if not artifact.get("verification_notes"):
            issues.append("Refine artifact must include verification_notes")

        return issues

    def _evaluate_phase_contracts(self) -> Dict[str, Any]:
        """Evaluate non-silent degradation contracts and store results."""
        contracts: Dict[str, Any] = {}

        for phase in self._required_contract_phases():
            artifact_path = self._get_phase_artifact_path(phase)
            artifact, issues = self._load_phase_artifact(phase)
            issues = list(issues)

            if artifact is not None:
                if phase == ResearchPhase.SCOPE:
                    issues = self._evaluate_scope_contract(artifact, issues)
                elif phase == ResearchPhase.PLAN:
                    issues = self._evaluate_plan_contract(artifact, issues)
                elif phase == ResearchPhase.RETRIEVE:
                    issues = self._evaluate_retrieve_contract(artifact, issues)
                elif phase == ResearchPhase.TRIANGULATE:
                    issues = self._evaluate_triangulate_contract(artifact, issues)
                elif phase == ResearchPhase.OUTLINE_REFINEMENT:
                    issues = self._evaluate_outline_refinement_contract(artifact, issues)
                elif phase == ResearchPhase.SYNTHESIZE:
                    issues = self._evaluate_synthesize_contract(artifact, issues)
                elif phase == ResearchPhase.CRITIQUE:
                    issues = self._evaluate_critique_contract(artifact, issues)
                elif phase == ResearchPhase.REFINE:
                    issues = self._evaluate_refine_contract(artifact, issues)

            if artifact is None:
                status = "missing"
            elif issues:
                status = "incomplete"
            else:
                status = "satisfied"

            contracts[phase.value] = {
                "required": True,
                "status": status,
                "artifact_path": str(artifact_path),
                "issues": issues,
                "artifact_status": artifact.get("status") if artifact else None,
                "checked_at": datetime.now().isoformat(),
            }

            if self.state is not None:
                phase_result = self.state.phase_results.setdefault(phase.value, {})
                phase_result["artifact_contract"] = contracts[phase.value]

        if self.state is not None:
            self.state.metadata["capability_contracts"] = contracts
            self.state.metadata["required_contracts_complete"] = all(
                contract["status"] == "satisfied"
                for contract in contracts.values()
            )

        return contracts

    def _resume_command_for(self, state_path: Path) -> str:
        """Build a copy-pastable resume command for the current runtime."""
        command = [
            sys.executable,
            "scripts/research_engine.py",
            "--resume",
            str(state_path),
            "--runtime",
            self.runtime.value,
        ]
        if self.pass_word_budget:
            command.extend(["--pass-word-budget", str(self.pass_word_budget)])
        return " ".join(command)

    def _resume_path_from_command(self, command: str) -> Optional[Path]:
        """Extract the resume state path from a recorded resume command."""
        if not command:
            return None

        try:
            tokens = shlex.split(command)
        except ValueError:
            return None

        for index, token in enumerate(tokens):
            if token == "--resume" and index + 1 < len(tokens):
                return Path(tokens[index + 1])
        return None

    def _auto_continue_signature(self) -> Tuple[Any, ...]:
        """Build a progress signature so auto-continue can detect stalled resumes."""
        if self.state is None:
            return tuple()

        next_action = self.state.metadata.get("next_action", {})
        validation = self.state.metadata.get("validation", {})
        validation_failures = tuple(
            key
            for key in ("validate_report", "verify_citations")
            if validation.get(key, {}).get("passed") is False
        )
        return (
            self.state.status,
            tuple(self.state.metadata.get("completed_section_ids", [])),
            tuple(self.state.metadata.get("pending_section_ids", [])),
            tuple(sorted(self._unresolved_contracts())),
            next_action.get("kind", ""),
            tuple(next_action.get("required_section_ids", [])),
            tuple(next_action.get("missing_contract_phases", [])),
            self.state.metadata.get("report_word_count", 0),
            validation_failures,
        )

    def _auto_continue_watch_paths(
        self,
        next_action: Dict[str, Any],
        resume_path: Optional[Path],
    ) -> List[Path]:
        """Return the files that should trigger the next auto-resume."""
        watch_paths: List[Path] = []

        for raw_path in next_action.get("required_files", []):
            if raw_path:
                watch_paths.append(Path(raw_path))

        if resume_path is not None:
            watch_paths.append(resume_path)

        if self.state is not None:
            watch_paths.append(self._get_report_path())
            watch_paths.append(self._get_run_state_path())

        deduped: List[Path] = []
        seen = set()
        for path in watch_paths:
            normalized = str(path.resolve()) if path.exists() else str(path.absolute())
            if normalized in seen:
                continue
            seen.add(normalized)
            deduped.append(path)
        return deduped

    def _snapshot_paths(self, paths: List[Path]) -> Dict[str, Tuple[bool, Optional[int], Optional[int]]]:
        """Snapshot existence, mtime, and size for a list of paths."""
        snapshot: Dict[str, Tuple[bool, Optional[int], Optional[int]]] = {}
        for path in paths:
            key = str(path.resolve()) if path.exists() else str(path.absolute())
            try:
                stat = path.stat()
            except FileNotFoundError:
                snapshot[key] = (False, None, None)
                continue
            snapshot[key] = (True, stat.st_mtime_ns, stat.st_size)
        return snapshot

    def _watch_paths_newer_than_run_state(self, paths: List[Path]) -> bool:
        """Check whether any watched file changed after the last run_state save."""
        run_state_path = self._get_run_state_path()
        if not run_state_path.exists():
            return False

        reference_mtime = run_state_path.stat().st_mtime_ns
        for path in paths:
            try:
                if path.stat().st_mtime_ns > reference_mtime:
                    return True
            except FileNotFoundError:
                continue
        return False

    def _format_watched_paths(self, paths: List[Path]) -> str:
        """Render watched paths with current existence and timestamp information."""
        lines: List[str] = []
        for path in paths:
            try:
                stat = path.stat()
            except FileNotFoundError:
                lines.append(f"  - {path} [missing]")
                continue

            modified_at = datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds")
            lines.append(
                f"  - {path} [exists, mtime={modified_at}, size={stat.st_size}B]"
            )
        return "\n".join(lines)

    def _wait_for_watched_paths(
        self,
        paths: List[Path],
        poll_interval: float,
        deadline: Optional[float],
    ) -> bool:
        """Wait until any watched file changes or the deadline expires."""
        baseline = self._snapshot_paths(paths)
        interval = max(poll_interval, 0.1)
        heartbeat_interval = max(AUTO_CONTINUE_HEARTBEAT_SECONDS, interval)
        wait_started_at = time.monotonic()
        next_heartbeat_at = wait_started_at + heartbeat_interval

        print("Auto-continue: entering wait state for watched files:")
        print(self._format_watched_paths(paths))

        while True:
            now = time.monotonic()
            if deadline is not None and now >= deadline:
                return False

            time.sleep(interval)
            current_snapshot = self._snapshot_paths(paths)
            if current_snapshot != baseline:
                print("Auto-continue: detected watched file change; continuing.")
                print(self._format_watched_paths(paths))
                return True

            now = time.monotonic()
            if now >= next_heartbeat_at:
                elapsed = int(now - wait_started_at)
                if deadline is None:
                    print(
                        "Auto-continue heartbeat: still waiting for file updates "
                        f"after {elapsed}s."
                    )
                else:
                    remaining = max(0, int(deadline - now))
                    print(
                        "Auto-continue heartbeat: still waiting for file updates "
                        f"after {elapsed}s (timeout in {remaining}s)."
                    )
                print(self._format_watched_paths(paths))
                next_heartbeat_at = now + heartbeat_interval

    def auto_continue_until_complete(
        self,
        query: str,
        timeout_seconds: float = 300.0,
        poll_interval: float = 1.0,
        max_resumes: int = 32,
    ) -> str:
        """Watch required files and automatically consume resume commands until done."""
        if self.state is None:
            raise ValueError("Research state is not initialized")

        deadline = None
        if timeout_seconds > 0:
            deadline = time.monotonic() + timeout_seconds

        resumes_performed = 0
        report_path = str(self._get_report_path())

        while self.state.status != "completed":
            if resumes_performed >= max_resumes:
                print(
                    "Auto-continue stopped: reached the maximum number of resumes "
                    f"({max_resumes})."
                )
                break

            next_action = self.state.metadata.get("next_action", {})
            resume_command = next_action.get("resume_command", "")
            if not resume_command:
                print("Auto-continue stopped: next_action did not include a resume command.")
                break

            resume_path = self._resume_path_from_command(resume_command)
            if resume_path is None:
                print(
                    "Auto-continue stopped: could not parse --resume from "
                    "next_action.resume_command."
                )
                break

            watch_paths = self._auto_continue_watch_paths(next_action, resume_path)
            signature_before_resume = self._auto_continue_signature()

            if self._watch_paths_newer_than_run_state(watch_paths):
                print(
                    "Auto-continue: detected file updates newer than run_state.json; "
                    f"resuming from {resume_path}."
                )
            else:
                print(
                    "Auto-continue: waiting for file updates before resuming.\n"
                    + self._format_watched_paths(watch_paths)
                )
                if not self._wait_for_watched_paths(watch_paths, poll_interval, deadline):
                    print(
                        "Auto-continue stopped: timed out waiting for required file updates."
                    )
                    break

            if not resume_path.exists():
                print(
                    "Auto-continue stopped: resume state no longer exists at "
                    f"{resume_path}."
                )
                break

            try:
                resume_kind = self.load_resume_state(resume_path)
            except (FileNotFoundError, KeyError, json.JSONDecodeError, ValueError) as exc:
                print(
                    "Auto-continue stopped: could not resume from "
                    f"{resume_path}: {exc}"
                )
                break

            print(f"Auto-continue: resuming from {resume_path} ({resume_kind}).")
            report_path = self.run_pipeline(query)
            resumes_performed += 1

            if (
                self.state.status != "completed"
                and self._auto_continue_signature() == signature_before_resume
            ):
                print(
                    "Auto-continue stopped: resume completed without any state progress. "
                    "Inspect the required files and rerun manually if needed."
                )
                break

        return report_path

    def _unresolved_contracts(self) -> Dict[str, Any]:
        """Return required contracts that are still unsatisfied."""
        if self.state is None:
            return {}

        contracts = self.state.metadata.get("capability_contracts", {})
        return {
            phase: contract
            for phase, contract in contracts.items()
            if contract.get("required") and contract.get("status") != "satisfied"
        }

    def _validation_failures(self) -> List[str]:
        """Return the names of validation helpers that are currently failing."""
        if self.state is None:
            return []

        validation = self.state.metadata.get("validation", {})
        failures = []
        for key in ("validate_report", "verify_citations"):
            result = validation.get(key, {})
            if result and result.get("passed") is False:
                failures.append(key)
        return failures

    def _update_next_action(self, next_sections: List[SectionCheckpoint]):
        """Record the single next action a user or runtime should take."""
        if self.state is None:
            return

        unresolved_contracts = self._unresolved_contracts()
        validation_failures = self._validation_failures()
        continuation_path = self._get_continuation_state_path()
        run_state_path = self._get_run_state_path()
        continuation_active = bool(
            self.state.metadata.get("section_progress", {}).get("continuation_active")
        )

        if self.state.status == "completed":
            next_action = {
                "kind": "complete",
                "required_files": [],
                "required_section_ids": [],
                "missing_contract_phases": [],
                "resume_command": "",
                "blocking_reason": "",
            }
        elif self.state.status == "needs_validation_fix":
            next_action = {
                "kind": "fix_validation",
                "required_files": [str(self._get_report_path())],
                "required_section_ids": [],
                "missing_contract_phases": [],
                "resume_command": self._resume_command_for(run_state_path),
                "blocking_reason": (
                    "Validation failed for: " + ", ".join(validation_failures)
                    if validation_failures
                    else "Validation failed; inspect report.md and rerun."
                ),
            }
        elif not self.state.metadata.get("pending_section_ids") and unresolved_contracts:
            next_action = {
                "kind": "fill_artifacts",
                "required_files": [
                    contract["artifact_path"] for contract in unresolved_contracts.values()
                ],
                "required_section_ids": [],
                "missing_contract_phases": sorted(unresolved_contracts),
                "resume_command": self._resume_command_for(run_state_path),
                "blocking_reason": "Required phase contract artifacts are incomplete.",
            }
        else:
            resume_path = continuation_path if continuation_active else run_state_path
            next_action = {
                "kind": "write_sections",
                "required_files": [str(self._get_report_path())],
                "required_section_ids": [item.section_id for item in next_sections],
                "missing_contract_phases": sorted(unresolved_contracts),
                "resume_command": self._resume_command_for(resume_path),
                "blocking_reason": "Report sections are still incomplete.",
            }

        self.state.metadata["next_action"] = next_action

    def _extract_block(
        self,
        content: str,
        start_pattern: str,
        next_pattern: str,
    ) -> Optional[Tuple[str, str]]:
        """Extract one markdown section block and its body."""
        start_match = re.search(start_pattern, content, re.MULTILINE | re.IGNORECASE)
        if not start_match:
            return None

        next_match = re.search(
            next_pattern,
            content[start_match.end():],
            re.MULTILINE | re.IGNORECASE,
        )
        end = start_match.end() + next_match.start() if next_match else len(content)
        block = content[start_match.start():end].strip()
        lines = block.splitlines()
        heading_line = lines[0].strip() if lines else ""
        body = "\n".join(lines[1:]).strip() if len(lines) > 1 else ""
        return heading_line, body

    def _extract_top_level_section(
        self,
        content: str,
        heading_patterns: List[str],
    ) -> Optional[Tuple[str, str]]:
        """Extract a top-level section using one of several heading patterns."""
        for pattern in heading_patterns:
            result = self._extract_block(content, pattern, r"^\s*##\s+")
            if result:
                return result
        return None

    def _extract_finding_section(
        self,
        content: str,
        finding_number: int,
    ) -> Optional[Tuple[str, str]]:
        """Extract one numbered finding section."""
        return self._extract_block(
            content,
            get_finding_pattern(finding_number),
            r"^\s*(?:(?:###\s+(?:Finding|发现)\s+\d+\s*(?:[:：-]\s*.*)?)|##\s+)",
        )

    def _ensure_finding_checkpoints(self, finding_count: int):
        """Add checkpoint slots when the report contains more findings than planned."""
        if self.state is None or finding_count <= 0:
            return

        existing_numbers = set()
        synthesis_index = len(self.state.section_checkpoints)

        for index, checkpoint in enumerate(self.state.section_checkpoints):
            if checkpoint.section_type == "finding":
                number = self._finding_number(checkpoint.section_id)
                if number is not None:
                    existing_numbers.add(number)
            elif checkpoint.section_id == "synthesis_insights":
                synthesis_index = index
                break

        for number in range(1, finding_count + 1):
            if number in existing_numbers:
                continue
            checkpoint = self._make_checkpoint(
                f"finding_{number}",
                f"发现 {number}",
                "finding",
                get_default_finding_heading(number),
                SECTION_TARGETS[self.mode]["finding"],
            )
            self.state.section_checkpoints.insert(synthesis_index, checkpoint)
            synthesis_index += 1

    def _finding_number(self, section_id: str) -> Optional[int]:
        """Return the numeric suffix for finding section ids."""
        match = re.match(r"finding_(\d+)$", section_id)
        return int(match.group(1)) if match else None

    def _section_complete(
        self,
        checkpoint: SectionCheckpoint,
        body: str,
        full_block: str,
    ) -> bool:
        """Decide whether a section should be marked complete."""
        if checkpoint.section_type == "bibliography":
            return bool(re.findall(r"^\[\d+\]", body, re.MULTILINE))

        min_words = SECTION_MIN_WORDS[checkpoint.section_type]
        return self._count_words(body) >= min_length_for_section(min_words, body) and len(full_block.strip()) > 0

    def _summarize_text(self, text: str, max_words: int = 24) -> str:
        """Create a short plain-text summary for handoff state."""
        if not text.strip():
            return ""

        if re.search(r"[\u3400-\u4DBF\u4E00-\u9FFF\uF900-\uFAFF]", text):
            visible_text = re.sub(r"\s+", " ", text).strip()
            summary = visible_text[: max_words * 4]
            if len(visible_text) > len(summary):
                summary += " ..."
            return summary

        words = re.findall(r"\b\w[\w'-]*\b", text)
        if not words:
            return ""
        summary_words = words[:max_words]
        summary = " ".join(summary_words)
        if len(words) > max_words:
            summary += " ..."
        return summary

    def _sync_section_checkpoints(self, report_content: str):
        """Sync checkpoint status from the current report contents."""
        if self.state is None:
            return

        found_finding_numbers = [
            int(match.group(1))
            for match in re.finditer(
                get_any_finding_pattern(),
                report_content,
                re.MULTILINE | re.IGNORECASE,
            )
        ]
        if found_finding_numbers:
            self._ensure_finding_checkpoints(max(found_finding_numbers))

        for checkpoint in self.state.section_checkpoints:
            if checkpoint.section_type == "finding":
                finding_number = self._finding_number(checkpoint.section_id)
                result = self._extract_finding_section(report_content, finding_number or 0)
            elif checkpoint.section_id == "executive_summary":
                result = self._extract_top_level_section(
                    report_content,
                    list(SECTION_PATTERNS_BY_ID["executive_summary"]),
                )
            elif checkpoint.section_id == "introduction":
                result = self._extract_top_level_section(
                    report_content,
                    list(SECTION_PATTERNS_BY_ID["introduction"]),
                )
            elif checkpoint.section_id == "synthesis_insights":
                result = self._extract_top_level_section(
                    report_content,
                    list(SECTION_PATTERNS_BY_ID["synthesis_insights"]),
                )
            elif checkpoint.section_id == "limitations_caveats":
                result = self._extract_top_level_section(
                    report_content,
                    list(SECTION_PATTERNS_BY_ID["limitations_caveats"]),
                )
            elif checkpoint.section_id == "recommendations":
                result = self._extract_top_level_section(
                    report_content,
                    list(SECTION_PATTERNS_BY_ID["recommendations"]),
                )
            elif checkpoint.section_id == "bibliography":
                result = self._extract_top_level_section(
                    report_content,
                    list(SECTION_PATTERNS_BY_ID["bibliography"]),
                )
            elif checkpoint.section_id == "methodology_appendix":
                result = self._extract_top_level_section(
                    report_content,
                    list(SECTION_PATTERNS_BY_ID["methodology_appendix"]),
                )
            else:
                result = None

            if not result:
                checkpoint.status = "pending"
                checkpoint.actual_words = 0
                checkpoint.citations_used = []
                checkpoint.summary = ""
                checkpoint.started_at = None
                checkpoint.completed_at = None
                continue

            heading_line, body = result
            full_block = "\n".join([heading_line, body]).strip()
            checkpoint.heading = heading_line or checkpoint.heading
            checkpoint.actual_words = self._count_words(body)
            checkpoint.citations_used = sorted(
                {int(item) for item in re.findall(r"\[(\d+)\]", full_block)}
            )
            checkpoint.summary = self._summarize_text(body)

            if checkpoint.started_at is None:
                checkpoint.started_at = datetime.now().isoformat()

            if self._section_complete(checkpoint, body, full_block):
                checkpoint.status = "completed"
                checkpoint.completed_at = checkpoint.completed_at or datetime.now().isoformat()
                if checkpoint.section_type == "finding":
                    title_match = re.match(
                        r"^\s*###\s+(?:Finding|发现)\s+\d+\s*(?:[:：-]\s*)?(.*)$",
                        heading_line,
                        re.IGNORECASE,
                    )
                    if title_match:
                        cleaned_title = title_match.group(1).strip()
                        if cleaned_title:
                            checkpoint.title = cleaned_title
            else:
                checkpoint.status = "in_progress"
                checkpoint.completed_at = None

    def _estimate_prose_ratio(self, content: str) -> str:
        """Estimate prose vs bullet ratio for continuation metadata."""
        lines = [line.strip() for line in content.splitlines() if line.strip()]
        if not lines:
            return "100% prose"

        body_lines = [line for line in lines if not line.startswith("#")]
        if not body_lines:
            return "100% prose"

        bullet_lines = sum(
            1
            for line in body_lines
            if re.match(r"^(?:[-*]\s+|\d+\.\s+)", line)
        )
        prose_lines = max(len(body_lines) - bullet_lines, 0)
        ratio = int(round((prose_lines / len(body_lines)) * 100))
        return f"{ratio}% prose"

    def _extract_bibliography_entries(self, report_content: str) -> List[str]:
        """Extract bibliography entries from the report."""
        result = self._extract_top_level_section(
            report_content,
            list(SECTION_PATTERNS_BY_ID["bibliography"]),
        )
        if not result:
            return []

        _, body = result
        return [
            line.strip()
            for line in body.splitlines()
            if re.match(r"^\[\d+\]", line.strip())
        ]

    def _build_citation_state(self, report_content: str) -> Dict[str, Any]:
        """Create continuation citation metadata."""
        ledger = self._load_sources_ledger()
        used_citations = sorted(
            {int(item) for item in re.findall(r"\[(\d+)\]", report_content)}
        )

        ledger_numbers = []
        for item in ledger:
            try:
                ledger_numbers.append(int(item.get("num")))
            except (TypeError, ValueError):
                continue

        bibliography_entries = self._extract_bibliography_entries(report_content)
        if not bibliography_entries:
            bibliography_entries = []
            for item in ledger:
                if not item.get("num") or not item.get("title"):
                    continue
                bibliography_entries.append(
                    f"[{item['num']}] {item['title']} - {item.get('url', 'unknown source')}"
                )

        highest_number = max(used_citations + ledger_numbers, default=0)
        return {
            "used": used_citations,
            "next_number": highest_number + 1,
            "bibliography_entries": bibliography_entries,
        }

    def _build_research_context(self) -> Dict[str, Any]:
        """Create continuation research context."""
        if self.state is None:
            return {}

        completed_findings = [
            item
            for item in self.state.section_checkpoints
            if item.section_type == "finding" and item.status == "completed"
        ]
        key_themes = list(self.state.scope.get("core_components", []))
        if not key_themes:
            key_themes = [item.title for item in completed_findings[:5]]
        if not key_themes:
            key_themes = [self.state.query]

        completion_ratio = self._completion_ratio()
        if completion_ratio == 0:
            narrative_arc = "opening"
        elif completion_ratio < 1:
            narrative_arc = "middle"
        else:
            narrative_arc = "final"

        return {
            "research_question": self.state.query,
            "key_themes": key_themes[:5],
            "main_findings_summary": [
                f"{item.title}: {item.summary}"
                for item in completed_findings[:3]
                if item.summary
            ],
            "narrative_arc": narrative_arc,
        }

    def _build_quality_metrics(self, report_content: str) -> Dict[str, Any]:
        """Create quality metrics for continuation handoff."""
        if self.state is None:
            return {}

        completed_findings = [
            item.actual_words
            for item in self.state.section_checkpoints
            if item.section_type == "finding" and item.status == "completed"
        ]
        avg_finding_words = (
            int(sum(completed_findings) / len(completed_findings))
            if completed_findings
            else SECTION_TARGETS[self.mode]["finding"]
        )

        report_word_count = max(self._count_words(report_content), 1)
        citation_density = round(
            len(re.findall(r"\[(\d+)\]", report_content)) / (report_word_count / 1000),
            2,
        )

        return {
            "avg_words_per_finding": avg_finding_words,
            "citation_density": citation_density,
            "prose_vs_bullets_ratio": self._estimate_prose_ratio(report_content),
            "writing_style": self.state.metadata.get(
                "writing_style",
                "technical-precise-data-driven",
            ),
        }

    def _completion_ratio(self) -> float:
        """Return section completion ratio."""
        if self.state is None or not self.state.section_checkpoints:
            return 0.0

        completed = len(
            [item for item in self.state.section_checkpoints if item.status == "completed"]
        )
        return completed / len(self.state.section_checkpoints)

    def _select_next_sections(self) -> List[SectionCheckpoint]:
        """Pick the next clean batch of incomplete sections for the current pass."""
        if self.state is None:
            return []

        pending = [
            item
            for item in self.state.section_checkpoints
            if item.status != "completed"
        ]
        if not pending:
            return []

        selected: List[SectionCheckpoint] = []
        accumulated_words = 0

        for checkpoint in pending:
            if selected and accumulated_words + checkpoint.target_words > self.pass_word_budget:
                break
            selected.append(checkpoint)
            accumulated_words += checkpoint.target_words

        return selected or pending[:1]

    def _refresh_status(self, report_content: str) -> List[SectionCheckpoint]:
        """Refresh overall run status and metadata."""
        if self.state is None:
            return []

        report_word_count = self._count_words(report_content)
        completed_ids = [
            item.section_id
            for item in self.state.section_checkpoints
            if item.status == "completed"
        ]
        pending_ids = [
            item.section_id
            for item in self.state.section_checkpoints
            if item.status != "completed"
        ]
        next_sections = self._select_next_sections()
        planned_total_words = sum(
            item.target_words for item in self.state.section_checkpoints
        )

        continuation_active = bool(pending_ids) and (
            planned_total_words > self.pass_word_budget
            or bool(completed_ids)
            or self._resume_source == "continuation_state"
            or self._get_continuation_state_path().exists()
            or int(self.state.metadata.get("continuation_count", 0)) > 0
        )

        if not pending_ids:
            self.state.status = "ready_for_validation"
        elif completed_ids:
            self.state.status = "in_progress"
        elif continuation_active:
            self.state.status = "awaiting_sections"
        else:
            self.state.status = "planned"

        self.state.metadata["report_word_count"] = report_word_count
        self.state.metadata["completed_section_ids"] = completed_ids
        self.state.metadata["pending_section_ids"] = pending_ids
        self.state.metadata["next_section_ids"] = [
            item.section_id for item in next_sections
        ]
        self.state.metadata["section_progress"] = {
            "completed": len(completed_ids),
            "total": len(self.state.section_checkpoints),
            "report_word_count": report_word_count,
            "continuation_active": continuation_active,
        }
        self.state.metadata["sources_ledger_count"] = len(self._load_sources_ledger())
        self.state.metadata["last_synced_at"] = datetime.now().isoformat()

        return next_sections

    def _run_validation_script(self, script_name: str, extra_args: Optional[List[str]] = None) -> Dict[str, Any]:
        """Run one validation helper and capture its result."""
        command = [sys.executable, str(self._scripts_dir / script_name), "--report", str(self._get_report_path())]
        if extra_args:
            command.extend(extra_args)

        try:
            completed = subprocess.run(
                command,
                text=True,
                capture_output=True,
                timeout=45,
            )
            return {
                "command": command,
                "exit_code": completed.returncode,
                "passed": completed.returncode == 0,
                "stdout": completed.stdout[-4000:],
                "stderr": completed.stderr[-4000:],
                "ran_at": datetime.now().isoformat(),
                "timed_out": False,
            }
        except subprocess.TimeoutExpired as exc:
            return {
                "command": command,
                "exit_code": None,
                "passed": False,
                "stdout": (exc.stdout or "")[-4000:],
                "stderr": ((exc.stderr or "") + "\nValidation timed out")[-4000:],
                "ran_at": datetime.now().isoformat(),
                "timed_out": True,
            }

    def _run_completion_validation(self):
        """Run final validation when all sections are present."""
        if self.state is None:
            return

        validate_result = self._run_validation_script("validate_report.py")
        citation_result = self._run_validation_script("verify_citations.py")
        validation_state = {
            "validate_report": validate_result,
            "verify_citations": citation_result,
            "all_passed": validate_result["passed"] and citation_result["passed"],
            "last_run_at": datetime.now().isoformat(),
        }
        self.state.metadata["validation"] = validation_state

        if validation_state["all_passed"]:
            if self.state.metadata.get("required_contracts_complete", True):
                self.state.status = "completed"
            else:
                self.state.status = "needs_contract_fix"
        else:
            self.state.status = "needs_validation_fix"

    def refresh_state_from_artifacts(self):
        """Update run state from report.md and sources.json."""
        if self.state is None:
            raise ValueError("Research state is not initialized")

        self._bootstrap_loaded_state()
        report_path = self._get_report_path()
        report_content = report_path.read_text(encoding="utf-8")
        self.state.report = report_content
        self._sync_section_checkpoints(report_content)
        self._sync_sources_from_report(report_content)
        self._evaluate_phase_contracts()
        next_sections = self._refresh_status(report_content)
        if self.state.status == "ready_for_validation":
            self._run_completion_validation()
        elif self.state.status != "completed":
            self.state.metadata["validation"] = {
                "status": "not_run",
                "reason": "report sections are still incomplete",
                "last_run_at": datetime.now().isoformat(),
            }
        self._update_next_action(next_sections)
        self._write_or_cleanup_continuation_state(report_content, next_sections)

    def _write_or_cleanup_continuation_state(
        self,
        report_content: str,
        next_sections: List[SectionCheckpoint],
    ):
        """Write continuation_state.json when needed, otherwise remove it."""
        if self.state is None:
            return

        continuation_path = self._get_continuation_state_path()
        pending = [
            item
            for item in self.state.section_checkpoints
            if item.status != "completed"
        ]
        progress = self.state.metadata.get("section_progress", {})
        continuation_active = bool(progress.get("continuation_active"))

        if not continuation_active or not pending:
            if continuation_path.exists():
                continuation_path.unlink()
            return

        continuation_state = ContinuationState(
            version=STATE_VERSION,
            report_id=self.state.metadata.get("report_id", self.output_dir.name),
            file_path=str(self._get_report_path()),
            mode=self.mode.value,
            progress={
                "sections_completed": self.state.metadata.get("completed_section_ids", []),
                "total_planned_sections": len(self.state.section_checkpoints),
                "word_count_so_far": self.state.metadata.get("report_word_count", 0),
                "continuation_count": int(
                    self.state.metadata.get("continuation_count", 0)
                ),
            },
            citations=self._build_citation_state(report_content),
            research_context=self._build_research_context(),
            quality_metrics=self._build_quality_metrics(report_content),
            next_sections=[item.to_continuation_payload() for item in next_sections],
            runtime=self.runtime.value,
            run_state_path=str(self._get_run_state_path()),
            generated_at=datetime.now().isoformat(),
        )
        continuation_state.save(continuation_path)

    def save_run_state(self) -> Path:
        """Persist the current orchestration checkpoint."""
        if self.state is None:
            raise ValueError("Research state is not initialized")

        self.refresh_state_from_artifacts()
        run_state_path = self._get_run_state_path()
        self.state.metadata["run_state_path"] = str(run_state_path)
        self.state.metadata["continuation_state_path"] = str(
            self._get_continuation_state_path()
        )
        self.state.save(run_state_path)
        return run_state_path

    def get_phase_instructions(self, phase: ResearchPhase) -> str:
        """Get instructions for the current phase."""
        instructions = {
            ResearchPhase.SCOPE: """
# Phase 1: SCOPE

Your task: Define research boundaries and success criteria

## Execute:
1. Decompose the question into 3-5 core components
2. Identify 2-4 key stakeholder perspectives
3. Define what's IN scope and what's OUT of scope
4. List 3-5 success criteria for this research
5. Document 3-5 assumptions that need validation

## Output Format:
```json
{
  "core_components": ["component1", "component2", "..."],
  "stakeholder_perspectives": ["perspective1", "perspective2", "..."],
  "in_scope": ["item1", "item2", "..."],
  "out_of_scope": ["item1", "item2", "..."],
  "success_criteria": ["criteria1", "criteria2", "..."],
  "assumptions": ["assumption1", "assumption2", "..."]
}
```
""",
            ResearchPhase.PLAN: """
# Phase 2: PLAN

Your task: Create an intelligent research roadmap

## Execute:
1. Identify 5-10 primary sources to investigate
2. List 5-10 secondary or backup sources
3. Map knowledge dependencies
4. Create 10-15 search query variations
5. Plan the triangulation approach
6. Define 3-5 quality gates
""",
            ResearchPhase.RETRIEVE: """
# Phase 3: RETRIEVE

Your task: Systematically collect information from multiple sources

## Execute:
1. Use the current environment's browse/search workflow with iterative refinement
2. In standard/deep/ultradeep, run 2-3 focused deep-dive tracks in parallel
3. Open and inspect 5-10 promising original sources
4. Extract key passages with metadata
5. Track information gaps and promising tangents
6. Preserve source diversity across domains and viewpoints

## Output:
Store all sources with metadata in memory and keep `sources.json` current as sections are written.
""",
            ResearchPhase.TRIANGULATE: """
# Phase 4: TRIANGULATE

Your task: Validate information across multiple independent sources

## Execute:
1. List all major claims from retrieved information
2. For each claim, find 3+ confirmatory sources when possible
3. Flag contradictions or uncertainties
4. Assess source credibility, recency, and bias
5. Mark verification status for each claim
""",
            ResearchPhase.OUTLINE_REFINEMENT: """
# Phase 4.5: OUTLINE REFINEMENT

Your task: Refine the report outline when evidence changes the shape of the story

## Execute:
1. Compare the initial plan with the evidence actually collected
2. Promote new themes that emerged as central
3. Demote sections that no longer justify space
4. Run short delta queries if the refined outline exposes a critical gap
5. Record why the outline changed
""",
            ResearchPhase.SYNTHESIZE: """
# Phase 5: SYNTHESIZE

Your task: Connect insights and generate useful understanding

## Execute:
1. Identify 5-10 key patterns across sources
2. Map relationships between concepts
3. Generate 3-5 insights that go beyond any single source
4. Separate facts, interpretation, and speculation clearly
5. Build the argument structure for the report
""",
            ResearchPhase.CRITIQUE: """
# Phase 6: CRITIQUE

Your task: Rigorously pressure-test research quality

## Execute:
1. Check logical consistency
2. Verify citation completeness
3. Identify gaps or weak evidence chains
4. Test alternative interpretations
5. Challenge assumptions and blind spots
6. In deep/ultradeep, simulate these mandatory personas:
   - Skeptical Practitioner
   - Adversarial Reviewer
   - Implementation Engineer
7. If a critical knowledge gap is found, return to targeted retrieval before packaging
""",
            ResearchPhase.REFINE: """
# Phase 7: REFINE

Your task: Close the highest-priority gaps from critique

## Execute:
1. Conduct additional research for identified gaps
2. Strengthen weak arguments with better evidence
3. Add missing perspectives
4. Resolve contradictions where possible
5. Improve clarity and structure
""",
            ResearchPhase.PACKAGE: """
# Phase 8: PACKAGE

Your task: Deliver the report through progressive section assembly

## Runtime Contract:
- Write one complete section at a time to `report.md`
- Keep `sources.json` current for citation provenance
- Keep `run_state.json` current for section-level checkpoints
- If another pass is required, use `continuation_state.json` as the handoff contract
- Do not present a partial report as complete

## Required Section Order:
1. Executive Summary
2. Introduction
3. Findings
4. Synthesis & Insights
5. Limitations & Caveats
6. Recommendations
7. Bibliography
8. Appendix: Methodology
""",
        }
        return instructions.get(phase, "No instructions available for this phase")

    def execute_phase(self, phase: ResearchPhase) -> Dict[str, Any]:
        """Execute a research phase by emitting instructions and updating stubs."""
        print(f"\n{'=' * 80}")
        print(f"PHASE {phase.value.upper()}: Starting...")
        print(f"{'=' * 80}\n")

        instructions = self.get_phase_instructions(phase)
        print(instructions)

        if phase in self._required_contract_phases():
            artifact_path = self._get_phase_artifact_path(phase)
            print(f"Artifact contract file: {artifact_path}")
            print("Fill this JSON artifact and rerun with --resume so the helper can verify the contract.\n")

        result = {
            "phase": phase.value,
            "status": "instructions_displayed",
            "timestamp": datetime.now().isoformat(),
        }
        if self.state is not None:
            self.state.phase_results[phase.value] = result
        return result

    def _print_section_progress(self):
        """Print a concise section progress summary."""
        if self.state is None:
            return

        completed = [
            item.title
            for item in self.state.section_checkpoints
            if item.status == "completed"
        ]
        next_sections = [
            item.title
            for item in self.state.section_checkpoints
            if item.section_id in self.state.metadata.get("next_section_ids", [])
        ]
        progress = self.state.metadata.get("section_progress", {})

        print(f"Report status: {self.state.status}")
        print(
            "Section progress: "
            f"{progress.get('completed', 0)}/{progress.get('total', 0)} completed"
        )
        if completed:
            print(f"Completed sections: {', '.join(completed)}")
        if next_sections:
            print(f"Next sections for this pass: {', '.join(next_sections)}")
        print(f"Report words so far: {progress.get('report_word_count', 0)}")

        continuation_path = self._get_continuation_state_path()
        if continuation_path.exists():
            print(f"Continuation state: {continuation_path}")
        else:
            print("Continuation state: not required right now")

        contracts = self.state.metadata.get("capability_contracts", {})
        unresolved = [
            f"{phase}: {', '.join(contract['issues'])}"
            for phase, contract in contracts.items()
            if contract.get("required") and contract.get("status") != "satisfied"
        ]
        if unresolved:
            print("Unresolved capability contracts:")
            for item in unresolved:
                print(f"  - {item}")

        next_action = self.state.metadata.get("next_action", {})
        if next_action:
            print("Next action:")
            print(f"  - Kind: {next_action.get('kind', 'unknown')}")
            required_sections = next_action.get("required_section_ids", [])
            if required_sections:
                print("  - Sections: " + ", ".join(required_sections))
            missing_contracts = next_action.get("missing_contract_phases", [])
            if missing_contracts:
                print("  - Missing contracts: " + ", ".join(missing_contracts))
            blocking_reason = next_action.get("blocking_reason")
            if blocking_reason:
                print(f"  - Reason: {blocking_reason}")
            resume_command = next_action.get("resume_command")
            if resume_command:
                print(f"  - Resume: {resume_command}")

    def run_pipeline(self, query: str) -> str:
        """Run the orchestration pipeline and refresh checkpoint artifacts."""
        print(f"\n{'#' * 80}")
        print("# DEEP RESEARCH ENGINE")
        print(f"# Query: {query}")
        print(f"# Mode: {self.mode.value}")
        print(f"# Runtime: {self.runtime.value}")
        print(f"# Runtime Adapter Reference: {self._get_runtime_reference()}")
        print(f"# Write Mode: {self.write_mode.value}")
        print(f"# Pass Word Budget: {self.pass_word_budget}")
        print(f"{'#' * 80}\n")

        if self.state is None:
            self.initialize_research(query)
        else:
            self._bootstrap_loaded_state()
            self.refresh_state_from_artifacts()

        phases = self._get_phases_for_mode()

        for phase in phases:
            self.state.phase = phase
            self.execute_phase(phase)
            state_file = self.save_run_state()
            print(f"\n✓ Phase {phase.value} checkpoint saved to: {state_file}\n")

        report_file = self._get_report_path()

        print(f"\n{'=' * 80}")
        if self.state.status == "completed":
            print("REPORT COMPLETE")
        else:
            print("ORCHESTRATION STATE UPDATED")
        print(f"Report path: {report_file}")
        print(f"Run state: {self._get_run_state_path()}")
        self._print_section_progress()
        self._print_post_run_guidance()
        print(f"{'=' * 80}\n")

        return str(report_file)

    def _get_phases_for_mode(self) -> List[ResearchPhase]:
        """Get phases based on research mode."""
        if self.mode == ResearchMode.QUICK:
            return [
                ResearchPhase.SCOPE,
                ResearchPhase.RETRIEVE,
                ResearchPhase.PACKAGE,
            ]
        if self.mode == ResearchMode.STANDARD:
            return [
                ResearchPhase.SCOPE,
                ResearchPhase.PLAN,
                ResearchPhase.RETRIEVE,
                ResearchPhase.TRIANGULATE,
                ResearchPhase.OUTLINE_REFINEMENT,
                ResearchPhase.SYNTHESIZE,
                ResearchPhase.PACKAGE,
            ]
        return list(ResearchPhase)


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Deep Research Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python research_engine.py --query "state of quantum computing 2026" --mode deep --runtime codex
  python research_engine.py --query "state of quantum computing 2026" --mode deep --runtime codex --skeleton-only
  python research_engine.py --query "state of quantum computing 2026" --mode deep --runtime codex --attempt-autowrite
  python research_engine.py --query "state of quantum computing 2026" --mode deep --runtime codex --auto-continue
  python research_engine.py --resume ./research_20260404_quantum_computing/run_state.json --runtime codex
  python research_engine.py --resume ./research_20260404_quantum_computing/continuation_state.json --runtime codex
        """,
    )

    parser.add_argument(
        "--query",
        "-q",
        type=str,
        help="Research question or topic",
    )
    parser.add_argument(
        "--mode",
        "-m",
        type=str,
        choices=["quick", "standard", "deep", "ultradeep"],
        default="standard",
        help="Research depth mode (default: standard)",
    )
    parser.add_argument(
        "--resume",
        type=str,
        help="Resume from saved run_state.json or continuation_state.json file",
    )
    parser.add_argument(
        "--runtime",
        type=str,
        choices=["generic", "codex", "opencode"],
        default="generic",
        help="Runtime adapter to use for orchestration guidance (default: generic)",
    )
    parser.add_argument(
        "--pass-word-budget",
        type=int,
        help="Optional per-pass target word budget for section batching",
    )
    write_mode_group = parser.add_mutually_exclusive_group()
    write_mode_group.add_argument(
        "--skeleton-only",
        action="store_true",
        help=(
            "Initialize phase artifacts, state files, and the report skeleton only. "
            "This is the default behavior."
        ),
    )
    write_mode_group.add_argument(
        "--attempt-autowrite",
        action="store_true",
        help=(
            "Mark the run as an automatic-writing attempt. In most runtimes the helper "
            "still mainly prepares artifacts and waits for the agent runtime or delegated "
            "subagents to perform retrieval and drafting."
        ),
    )
    parser.add_argument(
        "--auto-continue",
        action="store_true",
        help=(
            "Watch required files and automatically consume next_action.resume_command "
            "after external edits land"
        ),
    )
    parser.add_argument(
        "--auto-continue-timeout",
        type=float,
        default=300.0,
        help=(
            "Maximum seconds to wait for external file updates while auto-continue is "
            "active (default: 300; <=0 disables the timeout)"
        ),
    )
    parser.add_argument(
        "--auto-continue-poll",
        type=float,
        default=1.0,
        help="Polling interval in seconds for auto-continue file watching (default: 1.0)",
    )
    parser.add_argument(
        "--auto-continue-max-resumes",
        type=int,
        default=32,
        help="Maximum automatic resume attempts before stopping (default: 32)",
    )

    args = parser.parse_args()

    mode = ResearchMode(args.mode)
    runtime = RuntimeAdapter(args.runtime)
    write_mode = (
        WriteMode.ATTEMPT_AUTOWRITE
        if args.attempt_autowrite
        else WriteMode.SKELETON_ONLY
    )
    engine = ResearchEngine(
        mode=mode,
        runtime=runtime,
        pass_word_budget=args.pass_word_budget,
        write_mode=write_mode,
    )

    if args.resume:
        state_file = Path(args.resume)
        if not state_file.exists():
            print(f"Error: State file not found: {state_file}", file=sys.stderr)
            sys.exit(1)

        print(f"Loading resume state from: {state_file}")
        try:
            resume_kind = engine.load_resume_state(state_file)
        except (FileNotFoundError, KeyError, json.JSONDecodeError, ValueError) as exc:
            print(f"Error: could not resume from {state_file}: {exc}", file=sys.stderr)
            sys.exit(1)

        if args.mode != engine.state.mode.value:
            print(
                f"Warning: ignoring --mode {args.mode!r} and using resumed mode "
                f"{engine.state.mode.value!r}"
            )
        engine.mode = engine.state.mode
        if args.pass_word_budget is None:
            engine.pass_word_budget = DEFAULT_PASS_WORD_BUDGET[engine.mode]
        saved_write_mode = engine.state.metadata.get("write_mode")
        if saved_write_mode in WriteMode._value2member_map_:
            engine.write_mode = WriteMode(saved_write_mode)
        else:
            engine.write_mode = write_mode

        saved_runtime = engine.state.metadata.get("runtime")
        if args.runtime == "generic" and saved_runtime in RuntimeAdapter._value2member_map_:
            engine.runtime = RuntimeAdapter(saved_runtime)

        print(f"Resumed research from: {state_file} ({resume_kind})")

    query = args.query
    if engine.state is not None:
        if query and query != engine.state.query:
            print(
                f"Warning: ignoring --query {query!r} and using resumed query "
                f"{engine.state.query!r}"
            )
        query = engine.state.query

    if not query:
        parser.error("--query is required unless --resume provides an existing state")

    report_path = engine.run_pipeline(query)
    if args.auto_continue and engine.state and engine.state.status != "completed":
        report_path = engine.auto_continue_until_complete(
            query,
            timeout_seconds=args.auto_continue_timeout,
            poll_interval=args.auto_continue_poll,
            max_resumes=max(args.auto_continue_max_resumes, 1),
        )

    print(f"\nReport path: {report_path}")
    if engine.state and engine.state.status == "completed":
        print("Research report is complete.")
    else:
        print("Research artifacts initialized or refreshed; report body text is still incomplete.")


if __name__ == "__main__":
    main()
