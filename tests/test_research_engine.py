import json
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "research_engine.py"
SCRIPTS_DIR = REPO_ROOT / "scripts"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from report_contract import (  # noqa: E402
    EXECUTIVE_SUMMARY_MAX_WORDS,
    EXECUTIVE_SUMMARY_MIN_WORDS,
    REPORT_SECTION_TITLES,
    get_default_section_heading,
    get_default_section_title,
    resolve_section_id,
)


def run_engine(workdir: Path, *args: str) -> subprocess.CompletedProcess:
    """Run the orchestration helper in a temporary workspace."""
    command = [sys.executable, str(SCRIPT_PATH), *args]
    return subprocess.run(
        command,
        cwd=workdir,
        text=True,
        capture_output=True,
        check=True,
    )


def read_json(path: Path):
    """Read JSON from disk."""
    return json.loads(path.read_text(encoding="utf-8"))


def read_json_with_retry(path: Path, timeout: float = 2.0, interval: float = 0.05):
    """Read JSON from disk while tolerating concurrent rewrites."""
    deadline = time.time() + timeout
    last_error = None

    while time.time() < deadline:
        try:
            return read_json(path)
        except (FileNotFoundError, json.JSONDecodeError) as exc:
            last_error = exc
            time.sleep(interval)

    if last_error is not None:
        raise last_error
    raise FileNotFoundError(path)


def word_block(label: str, count: int) -> str:
    """Build a predictable text block with a desired word count."""
    return " ".join(f"{label}_{index}" for index in range(count))


@contextmanager
def local_http_server():
    """Serve a tiny local HTTP endpoint for deterministic URL verification."""

    class Handler(BaseHTTPRequestHandler):
        def do_HEAD(self):
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()

        def do_GET(self):
            body = b"ok"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format, *args):
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()


def render_section(section_payload: dict, report_content: str, base_url: str) -> str:
    """Render one synthetic markdown section that the helper can recognize."""
    section_id = section_payload["id"]
    heading = section_payload["heading"]
    chunks = []

    if section_id.startswith("finding_") and "## Main Analysis" not in report_content and "## 主要分析" not in report_content:
        chunks.append("## 主要分析\n")
        finding_number = section_id.split("_", 1)[1]
        heading = f"### 发现 {finding_number}：测试发现 {finding_number}"

    if section_id == "executive_summary":
        body = word_block("summary", 100) + " [1]"
    elif section_id == "introduction":
        body = word_block("intro", 140) + " [1]"
    elif section_id.startswith("finding_"):
        body = word_block(section_id, 180) + " [1] [2]"
    elif section_id == "synthesis_insights":
        body = word_block("synthesis", 130) + " [2]"
    elif section_id == "limitations_caveats":
        body = word_block("limitations", 110) + " [2]"
    elif section_id == "recommendations":
        body = word_block("recommendations", 110) + " [2]"
    elif section_id == "bibliography":
        body = f"[1] Example source - {base_url}/source-1\n[2] Example source - {base_url}/source-2"
    elif section_id == "methodology_appendix":
        body = word_block("methodology", 120)
    else:
        body = word_block(section_id, 80)

    chunks.append(f"{heading}\n\n{body}\n")
    return "\n".join(chunks)


def write_required_contract_artifacts(report_dir: Path, mode: str = "deep", critical_gap: bool = False):
    """Write valid capability contract artifacts for the helper."""
    scope_artifact = {
        "phase": "scope",
        "status": "completed",
        "updated_at": "2026-04-05T00:00:00",
        "notes": ["Scope framing complete"],
        "blocking_reason": "",
        "core_components": ["capabilities", "risks", "benchmarks"],
        "stakeholder_perspectives": ["operator", "reviewer", "implementer"],
        "in_scope": ["current capabilities", "limitations", "operational impact"],
        "out_of_scope": ["historical archive", "adjacent unrelated markets"],
        "success_criteria": ["major claims triangulated", "decision-relevant tradeoffs surfaced"],
        "assumptions": ["current public sources are representative"],
    }
    (report_dir / "phase_scope.json").write_text(
        json.dumps(scope_artifact, indent=2) + "\n",
        encoding="utf-8",
    )

    plan_artifact = {
        "phase": "plan",
        "status": "completed",
        "updated_at": "2026-04-05T00:00:00",
        "notes": ["Research roadmap complete"],
        "blocking_reason": "",
        "primary_source_types": ["documentation", "industry analysis", "benchmarks"],
        "secondary_source_types": ["news", "blog posts"],
        "knowledge_dependencies": [
            {"concept": "benchmark methodology", "depends_on": ["vendor docs"]},
            {"concept": "operational risk", "depends_on": ["case studies"]},
        ],
        "search_queries": [
            "topic overview",
            "topic limitations",
            "topic benchmarks",
            "topic adoption",
            "topic failure modes",
        ],
        "triangulation_strategy": [
            "Cross-check benchmarks against vendor docs and independent analysis",
            "Separate consensus findings from contested findings",
        ],
        "quality_gates": [
            "At least 3 source types",
            "Major claims have multiple supporting sources",
        ],
    }
    (report_dir / "phase_plan.json").write_text(
        json.dumps(plan_artifact, indent=2) + "\n",
        encoding="utf-8",
    )

    retrieve_artifact = {
        "phase": "retrieve",
        "status": "completed",
        "updated_at": "2026-04-05T00:00:00",
        "notes": ["Broad retrieval and deep dives complete"],
        "blocking_reason": "",
        "broad_searches": [
            {"query": "topic overview", "status": "completed", "results_count": 12},
            {"query": "topic limitations", "status": "completed", "results_count": 7},
        ],
        "deep_dive_tracks": [
            {
                "name": "primary_source_extraction",
                "focus": "Primary-source or academic extraction",
                "status": "completed",
                "evidence_count": 4,
                "notes": ["Captured primary evidence"],
            },
            {
                "name": "counterevidence_review",
                "focus": "Counterevidence and limitations review",
                "status": "completed",
                "evidence_count": 3,
                "notes": ["Captured limitations evidence"],
            },
            {
                "name": "implementation_validation",
                "focus": "Implementation, commercial, or domain-specific validation",
                "status": "completed",
                "evidence_count": 2,
                "notes": ["Captured implementation evidence"],
            },
        ],
        "source_inventory_summary": {
            "total_sources": 12,
            "source_types": ["documentation", "industry", "news"],
            "coverage_notes": ["Diverse coverage captured"],
        },
    }
    (report_dir / "phase_retrieve.json").write_text(
        json.dumps(retrieve_artifact, indent=2) + "\n",
        encoding="utf-8",
    )

    triangulate_artifact = {
        "phase": "triangulate",
        "status": "completed",
        "updated_at": "2026-04-05T00:00:00",
        "notes": ["Claim verification complete"],
        "blocking_reason": "",
        "claim_checks": [
            {
                "claim": "Primary claim is supported",
                "verification_status": "verified",
                "supporting_sources": ["source-1", "source-2", "source-3"],
                "notes": ["Cross-checked across source types"],
            },
            {
                "claim": "Secondary limitation exists",
                "verification_status": "contested",
                "supporting_sources": ["source-2", "source-4"],
                "notes": ["Mixed evidence retained"],
            },
        ],
        "consensus_topics": ["Core direction"],
        "contested_topics": ["Benchmark variance"],
        "unresolved_gaps": [],
    }
    (report_dir / "phase_triangulate.json").write_text(
        json.dumps(triangulate_artifact, indent=2) + "\n",
        encoding="utf-8",
    )

    outline_artifact = {
        "phase": "outline_refinement",
        "status": "completed",
        "updated_at": "2026-04-05T00:00:00",
        "notes": ["Outline refinement complete"],
        "blocking_reason": "",
        "decision": "refined",
        "initial_outline_summary": ["Intro", "Findings", "Recommendations"],
        "evidence_driven_rationale": ["Evidence elevated benchmark variance as a major theme"],
        "outline_changes": ["Added explicit limitations emphasis", "Reordered findings by evidence strength"],
        "critical_gap_fill_required": critical_gap,
        "gap_fill_queries": [
            {
                "query": "benchmark variance follow-up",
                "status": "completed",
                "notes": ["Gap filled before synthesis"],
            }
        ] if critical_gap else [],
        "final_outline_sections": [
            "Executive Summary",
            "Introduction",
            "Main Analysis",
            "Synthesis & Insights",
            "Limitations & Caveats",
            "Recommendations",
            "Bibliography",
            "Appendix: Methodology",
        ],
    }
    (report_dir / "phase_outline_refinement.json").write_text(
        json.dumps(outline_artifact, indent=2) + "\n",
        encoding="utf-8",
    )

    synthesize_artifact = {
        "phase": "synthesize",
        "status": "completed",
        "updated_at": "2026-04-05T00:00:00",
        "notes": ["Synthesis complete"],
        "blocking_reason": "",
        "patterns": [
            "Benchmark quality varies by workload",
            "Operational caveats matter more than marketing claims",
        ],
        "concept_relationships": [
            {
                "concept": "benchmark variance",
                "related_to": ["deployment risk", "vendor disclosure quality"],
            }
        ],
        "novel_insights": [
            "Operational readiness depends more on evidence consistency than on peak benchmark results",
        ],
        "frameworks": ["Evidence strength vs operational risk matrix"],
        "key_arguments": [
            {
                "argument": "Decision quality improves when benchmark evidence is triangulated with operational caveats",
                "supporting_evidence": ["source-1", "source-2"],
                "strength": "strong",
            }
        ],
        "synthesis_summary": [
            "The strongest path combines evidence quality checks with implementation realism",
        ],
    }
    (report_dir / "phase_synthesize.json").write_text(
        json.dumps(synthesize_artifact, indent=2) + "\n",
        encoding="utf-8",
    )

    if mode in {"deep", "ultradeep"}:
        critique_artifact = {
            "phase": "critique",
            "status": "completed",
            "updated_at": "2026-04-05T00:00:00",
            "notes": ["Persona critique complete"],
            "blocking_reason": "",
            "personas": [
                {
                    "name": "Skeptical Practitioner",
                    "status": "completed",
                    "key_objections": ["Operational caveat noted"],
                    "critical_gaps": ["Need benchmark follow-up"] if critical_gap else [],
                    "resolution_notes": ["Benchmarks reviewed"],
                },
                {
                    "name": "Adversarial Reviewer",
                    "status": "completed",
                    "key_objections": ["Evidence mix challenged"],
                    "critical_gaps": [],
                    "resolution_notes": ["Triangulation retained"],
                },
                {
                    "name": "Implementation Engineer",
                    "status": "completed",
                    "key_objections": ["Execution plan clarified"],
                    "critical_gaps": [],
                    "resolution_notes": ["Implementation path documented"],
                },
            ],
            "critical_gap_found": critical_gap,
            "delta_queries_run": [
                {
                    "query": "benchmark delta query",
                    "status": "completed",
                    "notes": ["Gap closed"],
                }
            ] if critical_gap else [],
            "resolution_summary": ["Critique findings resolved"],
        }
        (report_dir / "phase_critique.json").write_text(
            json.dumps(critique_artifact, indent=2) + "\n",
            encoding="utf-8",
        )

        refine_artifact = {
            "phase": "refine",
            "status": "completed",
            "updated_at": "2026-04-05T00:00:00",
            "notes": ["Refinement complete"],
            "blocking_reason": "",
            "addressed_issues": [
                "Strengthened benchmark evidence",
                "Clarified operational caveats",
            ],
            "follow_up_retrieval": [
                {
                    "query": "benchmark variance reconciliation",
                    "status": "completed",
                    "notes": ["Additional evidence captured"],
                }
            ],
            "strengthened_claims": [
                "Operational benchmark claim now cites multiple sources",
            ],
            "remaining_limitations": ["Long-term data remains sparse"],
            "verification_notes": ["Re-checked revised sections against bibliography"],
        }
        (report_dir / "phase_refine.json").write_text(
            json.dumps(refine_artifact, indent=2) + "\n",
            encoding="utf-8",
        )


class ResearchEngineStateTests(unittest.TestCase):
    def test_initial_run_records_next_action_and_resume_command(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workdir = Path(temp_dir)

            initial = run_engine(
                workdir,
                "--query",
                "initial next action regression test",
                "--mode",
                "deep",
                "--runtime",
                "codex",
                "--pass-word-budget",
                "1600",
            )
            self.assertIn("Next action:", initial.stdout)

            report_dir = next(workdir.glob("research_*"))
            run_state = read_json(report_dir / "run_state.json")
            next_action = run_state["metadata"]["next_action"]

            self.assertEqual(next_action["kind"], "write_sections")
            self.assertEqual(
                next_action["required_section_ids"],
                ["executive_summary", "introduction"],
            )
            self.assertEqual(len(next_action["required_files"]), 1)
            self.assertEqual(
                Path(next_action["required_files"][0]).resolve(),
                (report_dir / "report.md").resolve(),
            )
            self.assertIn("continuation_state.json", next_action["resume_command"])
            self.assertIn("report sections are still incomplete", next_action["blocking_reason"].lower())
            self.assertEqual(run_state["metadata"]["write_mode"], "skeleton_only")
            self.assertIn("report body text is still incomplete", initial.stdout)
            self.assertIn("Current run only initialized research artifacts", initial.stdout)

    def test_continuation_and_section_checkpoint_flow(self):
        with tempfile.TemporaryDirectory() as temp_dir, local_http_server() as base_url:
            workdir = Path(temp_dir)

            initial = run_engine(
                workdir,
                "--query",
                "continuation regression test",
                "--mode",
                "deep",
                "--runtime",
                "codex",
                "--pass-word-budget",
                "1600",
            )
            self.assertIn("ORCHESTRATION STATE UPDATED", initial.stdout)

            report_dir = next(workdir.glob("research_*"))
            run_state_path = report_dir / "run_state.json"
            continuation_path = report_dir / "continuation_state.json"
            report_path = report_dir / "report.md"
            sources_path = report_dir / "sources.json"

            self.assertTrue(run_state_path.exists())
            self.assertTrue(continuation_path.exists())

            run_state = read_json(run_state_path)
            continuation = read_json(continuation_path)

            self.assertIn("section_checkpoints", run_state)
            self.assertGreater(len(run_state["section_checkpoints"]), 0)
            self.assertEqual(
                run_state["metadata"]["next_section_ids"],
                ["executive_summary", "introduction"],
            )
            self.assertEqual(
                [item["id"] for item in continuation["next_sections"]],
                ["executive_summary", "introduction"],
            )

            report_content = report_path.read_text(encoding="utf-8")
            for section in continuation["next_sections"]:
                report_content += render_section(section, report_content, base_url)
            report_path.write_text(report_content, encoding="utf-8")

            resumed = run_engine(
                workdir,
                "--resume",
                str(continuation_path),
                "--runtime",
                "codex",
                "--pass-word-budget",
                "1600",
            )
            self.assertIn("continuation_state", resumed.stdout)

            run_state = read_json(run_state_path)
            continuation = read_json(continuation_path)
            self.assertEqual(
                run_state["metadata"]["completed_section_ids"],
                ["executive_summary", "introduction"],
            )
            self.assertEqual(
                [item["id"] for item in continuation["next_sections"]],
                ["finding_1"],
            )

            report_content = report_path.read_text(encoding="utf-8")
            pending_sections = [
                item
                for item in run_state["section_checkpoints"]
                if item["status"] != "completed"
            ]
            for section in pending_sections:
                payload = {
                    "id": section["section_id"],
                    "heading": section["heading"],
                }
                report_content += render_section(payload, report_content, base_url)
            report_path.write_text(report_content, encoding="utf-8")
            write_required_contract_artifacts(report_dir, mode="deep", critical_gap=True)

            completed = run_engine(
                workdir,
                "--resume",
                str(run_state_path),
                "--runtime",
                "codex",
                "--pass-word-budget",
                "1600",
            )
            self.assertIn("REPORT COMPLETE", completed.stdout)
            self.assertFalse(continuation_path.exists())

            run_state = read_json(run_state_path)
            statuses = {item["status"] for item in run_state["section_checkpoints"]}
            self.assertEqual(statuses, {"completed"})
            self.assertEqual(run_state["status"], "completed")
            sources = read_json(sources_path)
            self.assertEqual([item["num"] for item in sources], [1, 2])
            self.assertTrue(all(item["claim"] for item in sources))

    def test_auto_continue_consumes_resume_chain_until_completed(self):
        with tempfile.TemporaryDirectory() as temp_dir, local_http_server() as base_url:
            workdir = Path(temp_dir)
            command = [
                sys.executable,
                str(SCRIPT_PATH),
                "--query",
                "auto continue regression test",
                "--mode",
                "deep",
                "--runtime",
                "codex",
                "--pass-word-budget",
                "4000",
                "--auto-continue",
                "--auto-continue-timeout",
                "20",
                "--auto-continue-poll",
                "0.2",
                "--auto-continue-max-resumes",
                "8",
            ]
            process = subprocess.Popen(
                command,
                cwd=workdir,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            deadline = time.time() + 20
            report_dir = None
            while time.time() < deadline:
                candidates = list(workdir.glob("research_*"))
                if candidates:
                    report_dir = candidates[0]
                    break
                time.sleep(0.1)

            self.assertIsNotNone(report_dir, "expected the helper to create a research_* directory")

            report_dir = report_dir or workdir
            run_state_path = report_dir / "run_state.json"
            report_path = report_dir / "report.md"
            continuation_path = report_dir / "continuation_state.json"
            handled_signatures = set()

            try:
                while time.time() < deadline:
                    if process.poll() is not None:
                        break
                    if not run_state_path.exists():
                        time.sleep(0.1)
                        continue

                    run_state = read_json_with_retry(run_state_path)
                    if run_state.get("phase") != "package":
                        time.sleep(0.1)
                        continue

                    next_action = run_state["metadata"]["next_action"]
                    signature = (
                        run_state["status"],
                        next_action.get("kind"),
                        tuple(next_action.get("required_section_ids", [])),
                        tuple(run_state["metadata"].get("completed_section_ids", [])),
                    )
                    if signature in handled_signatures:
                        time.sleep(0.1)
                        continue
                    handled_signatures.add(signature)

                    if next_action["kind"] == "write_sections":
                        checkpoint_map = {
                            item["section_id"]: item
                            for item in run_state["section_checkpoints"]
                        }
                        report_content = report_path.read_text(encoding="utf-8")
                        for section_id in next_action["required_section_ids"]:
                            payload = {
                                "id": section_id,
                                "heading": checkpoint_map[section_id]["heading"],
                            }
                            report_content += render_section(payload, report_content, base_url)
                        report_path.write_text(report_content, encoding="utf-8")
                    elif next_action["kind"] == "fill_artifacts":
                        write_required_contract_artifacts(
                            report_dir,
                            mode="deep",
                            critical_gap=True,
                        )
                    elif next_action["kind"] == "complete":
                        break
                    else:
                        self.fail(
                            f"unexpected next_action kind during auto-continue: {next_action['kind']}"
                        )

                    time.sleep(0.3)

                stdout, stderr = process.communicate(timeout=20)
            finally:
                if process.poll() is None:
                    process.terminate()
                    process.communicate(timeout=5)

            self.assertEqual(process.returncode, 0, msg=stderr)
            self.assertIn("Auto-continue:", stdout)
            self.assertIn("Research report is complete.", stdout)
            self.assertFalse(continuation_path.exists())

            run_state = read_json_with_retry(run_state_path)
            self.assertEqual(run_state["status"], "completed")
            self.assertEqual(
                {item["status"] for item in run_state["section_checkpoints"]},
                {"completed"},
            )

    def test_attempt_autowrite_flag_is_recorded_and_reported(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workdir = Path(temp_dir)

            result = run_engine(
                workdir,
                "--query",
                "autowrite mode regression test",
                "--mode",
                "standard",
                "--runtime",
                "codex",
                "--attempt-autowrite",
            )

            report_dir = next(workdir.glob("research_*"))
            run_state = read_json(report_dir / "run_state.json")

            self.assertEqual(run_state["metadata"]["write_mode"], "attempt_autowrite")
            self.assertIn("# Write Mode: attempt_autowrite", result.stdout)
            self.assertIn("Automatic writing mode requested", result.stdout)
            self.assertIn("report body text is still incomplete", result.stdout)

    def test_validation_failure_blocks_completed_status(self):
        with tempfile.TemporaryDirectory() as temp_dir, local_http_server() as base_url:
            workdir = Path(temp_dir)

            run_engine(
                workdir,
                "--query",
                "validation failure regression test",
                "--mode",
                "deep",
                "--runtime",
                "codex",
                "--pass-word-budget",
                "1600",
            )

            report_dir = next(workdir.glob("research_*"))
            run_state_path = report_dir / "run_state.json"
            report_path = report_dir / "report.md"

            report_path.write_text(
                "\n\n".join(
                    [
                        "## Executive Summary\n\n" + word_block("summary", 100) + " [1]",
                        "## Introduction\n\n" + word_block("intro", 140) + " [1]",
                        "## Main Analysis\n\n### Finding 1: Test finding 1\n\n" + word_block("finding1", 180) + " [1] [2]",
                        "### Finding 2: Test finding 2\n\n" + word_block("finding2", 180) + " [1] [2]",
                        "### Finding 3: Test finding 3\n\n" + word_block("finding3", 180) + " [1] [2]",
                        "### Finding 4: Test finding 4\n\n" + word_block("finding4", 180) + " [1] [2]",
                        "## Synthesis & Insights\n\n" + word_block("synthesis", 130) + " [2]",
                        "## Limitations & Caveats\n\n" + word_block("limitations", 110) + " TODO [2]",
                        "## Recommendations\n\n" + word_block("recommendations", 110) + " [2]",
                        f"## Bibliography\n\n[1] Example source - {base_url}/source-1\n[2] Example source - {base_url}/source-2",
                        "## Appendix: Methodology\n\n" + word_block("methodology", 120),
                    ]
                ),
                encoding="utf-8",
            )
            write_required_contract_artifacts(report_dir, mode="deep")

            rerun = run_engine(
                workdir,
                "--resume",
                str(run_state_path),
                "--runtime",
                "codex",
                "--pass-word-budget",
                "1600",
            )
            self.assertIn("ORCHESTRATION STATE UPDATED", rerun.stdout)

            run_state = read_json(run_state_path)
            self.assertEqual(run_state["status"], "needs_validation_fix")
            self.assertFalse(run_state["metadata"]["validation"]["all_passed"])
            self.assertFalse(run_state["metadata"]["validation"]["validate_report"]["passed"])
            self.assertEqual(run_state["metadata"]["next_action"]["kind"], "fix_validation")

    def test_missing_contract_blocks_completed_status(self):
        with tempfile.TemporaryDirectory() as temp_dir, local_http_server() as base_url:
            workdir = Path(temp_dir)

            run_engine(
                workdir,
                "--query",
                "contract regression test",
                "--mode",
                "deep",
                "--runtime",
                "codex",
                "--pass-word-budget",
                "1600",
            )

            report_dir = next(workdir.glob("research_*"))
            run_state_path = report_dir / "run_state.json"
            report_path = report_dir / "report.md"

            report_path.write_text(
                "\n\n".join(
                    [
                        "## Executive Summary\n\n" + word_block("summary", 100) + " [1]",
                        "## Introduction\n\n" + word_block("intro", 140) + " [1]",
                        "## Main Analysis\n\n### Finding 1: Test finding 1\n\n" + word_block("finding1", 180) + " [1] [2]",
                        "### Finding 2: Test finding 2\n\n" + word_block("finding2", 180) + " [1] [2]",
                        "### Finding 3: Test finding 3\n\n" + word_block("finding3", 180) + " [1] [2]",
                        "### Finding 4: Test finding 4\n\n" + word_block("finding4", 180) + " [1] [2]",
                        "## Synthesis & Insights\n\n" + word_block("synthesis", 130) + " [2]",
                        "## Limitations & Caveats\n\n" + word_block("limitations", 110) + " [2]",
                        "## Recommendations\n\n" + word_block("recommendations", 110) + " [2]",
                        f"## Bibliography\n\n[1] Example source - {base_url}/source-1\n[2] Example source - {base_url}/source-2",
                        "## Appendix: Methodology\n\n" + word_block("methodology", 120),
                    ]
                ),
                encoding="utf-8",
            )

            rerun = run_engine(
                workdir,
                "--resume",
                str(run_state_path),
                "--runtime",
                "codex",
                "--pass-word-budget",
                "1600",
            )
            self.assertIn("ORCHESTRATION STATE UPDATED", rerun.stdout)

            run_state = read_json(run_state_path)
            self.assertEqual(run_state["status"], "needs_contract_fix")
            contracts = run_state["metadata"]["capability_contracts"]
            self.assertEqual(contracts["scope"]["status"], "incomplete")
            self.assertEqual(contracts["plan"]["status"], "incomplete")
            self.assertEqual(contracts["retrieve"]["status"], "incomplete")
            self.assertEqual(contracts["triangulate"]["status"], "incomplete")
            self.assertEqual(contracts["outline_refinement"]["status"], "incomplete")
            self.assertEqual(contracts["synthesize"]["status"], "incomplete")
            self.assertEqual(contracts["critique"]["status"], "incomplete")
            self.assertEqual(contracts["refine"]["status"], "incomplete")
            self.assertTrue(run_state["metadata"]["validation"]["all_passed"])
            self.assertEqual(run_state["metadata"]["next_action"]["kind"], "fill_artifacts")

    def test_shared_contract_values_match_default_template_expectations(self):
        self.assertEqual(REPORT_SECTION_TITLES, (
            "Executive Summary",
            "Introduction",
            "Main Analysis",
            "Synthesis & Insights",
            "Limitations & Caveats",
            "Recommendations",
            "Bibliography",
            "Appendix: Methodology",
        ))
        self.assertEqual(EXECUTIVE_SUMMARY_MIN_WORDS, 50)
        self.assertEqual(EXECUTIVE_SUMMARY_MAX_WORDS, 400)

    def test_default_section_plan_uses_chinese_visible_headings(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workdir = Path(temp_dir)
            initial = run_engine(
                workdir,
                "--query",
                "default chinese headings regression test",
                "--mode",
                "standard",
                "--runtime",
                "codex",
            )
            self.assertIn("ORCHESTRATION STATE UPDATED", initial.stdout)

            report_dir = next(workdir.glob("research_*"))
            run_state = read_json(report_dir / "run_state.json")
            checkpoints = {
                item["section_id"]: item
                for item in run_state["section_checkpoints"]
            }

            self.assertEqual(
                checkpoints["executive_summary"]["heading"],
                get_default_section_heading("executive_summary"),
            )
            self.assertEqual(
                checkpoints["introduction"]["heading"],
                get_default_section_heading("introduction"),
            )
            self.assertEqual(
                checkpoints["bibliography"]["heading"],
                get_default_section_heading("bibliography"),
            )
            self.assertEqual(
                checkpoints["executive_summary"]["title"],
                get_default_section_title("executive_summary"),
            )

    def test_resume_recognizes_chinese_sections_as_completed(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workdir = Path(temp_dir)
            run_engine(
                workdir,
                "--query",
                "chinese section completion regression test",
                "--mode",
                "standard",
                "--runtime",
                "codex",
            )

            report_dir = next(workdir.glob("research_*"))
            report_path = report_dir / "report.md"
            report_path.write_text(
                "\n\n".join(
                    [
                        "## 执行摘要\n\n"
                        + "这是一段足够长的中文摘要内容，用于验证默认中文标题与摘要识别逻辑，并覆盖主要结论、适用边界和关键建议。"
                        * 2
                        + "[1]\n第二句补充主要结论和适用边界，并说明为何需要保留中文默认输出。[2]",
                        "## 引言\n\n"
                        + "这里用中文说明研究范围、方法与关键假设，确保长度足够让状态机认定该章节已完成，同时保留必要引用。"
                        * 3
                        + "[1][2]",
                        "## 主要分析\n\n### 发现 1：测试发现 1\n\n"
                        + "这是一段用于验证中文发现章节完成判定的正文内容。" * 20
                        + "[1][2]",
                        "## 综合与洞察\n\n" + "综合结论内容。" * 30 + "[2]",
                        "## 局限性与注意事项\n\n" + "局限性说明。" * 20 + "[2]",
                        "## 建议\n\n" + "建议内容。" * 20 + "[2]",
                        "## 参考文献\n\n[1] Example source - https://example.com/source-1\n[2] Example source - https://example.com/source-2",
                        "## 附录：研究方法\n\n" + "研究方法说明。" * 20,
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            run_engine(
                workdir,
                "--resume",
                str(report_dir / "run_state.json"),
                "--runtime",
                "codex",
            )

            run_state = read_json(report_dir / "run_state.json")
            completed_ids = set(run_state["metadata"]["completed_section_ids"])
            self.assertEqual(run_state["status"], "in_progress")
            self.assertTrue(
                {
                    "executive_summary",
                    "introduction",
                    "finding_1",
                    "synthesis_insights",
                    "limitations_caveats",
                    "recommendations",
                    "bibliography",
                    "methodology_appendix",
                }.issubset(completed_ids)
            )

    def test_report_contract_resolves_chinese_section_aliases(self):
        self.assertEqual(resolve_section_id("执行摘要"), "executive_summary")
        self.assertEqual(resolve_section_id("## 主要分析"), "main_analysis")
        self.assertEqual(resolve_section_id("综合洞察"), "synthesis_insights")
        self.assertEqual(resolve_section_id("附录：研究方法"), "methodology_appendix")


if __name__ == "__main__":
    unittest.main()
