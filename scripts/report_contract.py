"""Shared report contract for the default markdown-first workflow."""

from __future__ import annotations

from typing import Dict, List, Tuple


EXECUTIVE_SUMMARY_MIN_WORDS = 50
EXECUTIVE_SUMMARY_MAX_WORDS = 400
MIN_REPORT_WORDS = 500
RECOMMENDED_MIN_SOURCES = 10


REPORT_SECTION_SPECS: List[Dict[str, object]] = [
    {
        "id": "executive_summary",
        "title": "Executive Summary",
        "heading_patterns": [r"^\s*##\s+Executive Summary\b.*$"],
    },
    {
        "id": "introduction",
        "title": "Introduction",
        "heading_patterns": [r"^\s*##\s+Introduction\b.*$"],
    },
    {
        "id": "main_analysis",
        "title": "Main Analysis",
        "heading_patterns": [r"^\s*##\s+Main Analysis\b.*$"],
    },
    {
        "id": "synthesis_insights",
        "title": "Synthesis & Insights",
        "heading_patterns": [
            r"^\s*##\s+Synthesis(?:\s*&\s*Insights)?\b.*$",
            r"^\s*##\s+Synthesis and Insights\b.*$",
        ],
    },
    {
        "id": "limitations_caveats",
        "title": "Limitations & Caveats",
        "heading_patterns": [
            r"^\s*##\s+Limitations(?:\s*&\s*Caveats)?\b.*$",
            r"^\s*##\s+Limitations and Caveats\b.*$",
        ],
    },
    {
        "id": "recommendations",
        "title": "Recommendations",
        "heading_patterns": [r"^\s*##\s+Recommendations\b.*$"],
    },
    {
        "id": "bibliography",
        "title": "Bibliography",
        "heading_patterns": [r"^\s*##\s+Bibliography\b.*$"],
    },
    {
        "id": "methodology_appendix",
        "title": "Appendix: Methodology",
        "heading_patterns": [
            r"^\s*##\s+Appendix:\s*Methodology\b.*$",
            r"^\s*##\s+Methodology Appendix\b.*$",
            r"^\s*##\s+Methodology\b.*$",
        ],
    },
]


REPORT_SECTION_TITLES: Tuple[str, ...] = tuple(
    str(spec["title"]) for spec in REPORT_SECTION_SPECS
)

SECTION_PATTERNS_BY_ID: Dict[str, Tuple[str, ...]] = {
    str(spec["id"]): tuple(str(pattern) for pattern in spec["heading_patterns"])
    for spec in REPORT_SECTION_SPECS
}
