"""Shared report contract for the default markdown-first workflow."""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple


EXECUTIVE_SUMMARY_MIN_WORDS = 50
EXECUTIVE_SUMMARY_MAX_WORDS = 400
MIN_REPORT_WORDS = 500
RECOMMENDED_MIN_SOURCES = 10
CJK_RATIO_THRESHOLD = 0.2
CJK_SECTION_CHAR_MULTIPLIER = 1

CJK_CHAR_RE = re.compile(r"[\u3400-\u4DBF\u4E00-\u9FFF\uF900-\uFAFF]")
WORD_RE = re.compile(r"\b\w+\b")
SUMMARY_UNIT_RE = re.compile(r"[。！？!?]+|(?<!\w)\.(?=\s|$)")
SUMMARY_BULLET_RE = re.compile(r"^\s*(?:[-*+]|\d+\.)\s+", re.MULTILINE)


REPORT_SECTION_SPECS: List[Dict[str, object]] = [
    {
        "id": "executive_summary",
        "title": "Executive Summary",
        "default_title": "执行摘要",
        "default_heading": "## 执行摘要",
        "aliases": ("Executive Summary", "执行摘要"),
        "heading_patterns": [
            r"^\s*##\s+Executive Summary\b.*$",
            r"^\s*##\s+执行摘要(?:\s|$|[:：-]).*$",
            r"^\s*##\s+执行摘要\s*$",
        ],
    },
    {
        "id": "introduction",
        "title": "Introduction",
        "default_title": "引言",
        "default_heading": "## 引言",
        "aliases": ("Introduction", "引言", "介绍"),
        "heading_patterns": [
            r"^\s*##\s+Introduction\b.*$",
            r"^\s*##\s+引言(?:\s|$|[:：-]).*$",
            r"^\s*##\s+引言\s*$",
            r"^\s*##\s+介绍(?:\s|$|[:：-]).*$",
            r"^\s*##\s+介绍\s*$",
        ],
    },
    {
        "id": "main_analysis",
        "title": "Main Analysis",
        "default_title": "主要分析",
        "default_heading": "## 主要分析",
        "aliases": ("Main Analysis", "主要分析"),
        "heading_patterns": [
            r"^\s*##\s+Main Analysis\b.*$",
            r"^\s*##\s+主要分析(?:\s|$|[:：-]).*$",
            r"^\s*##\s+主要分析\s*$",
        ],
    },
    {
        "id": "synthesis_insights",
        "title": "Synthesis & Insights",
        "default_title": "综合与洞察",
        "default_heading": "## 综合与洞察",
        "aliases": ("Synthesis & Insights", "Synthesis and Insights", "综合与洞察", "综合洞察"),
        "heading_patterns": [
            r"^\s*##\s+Synthesis(?:\s*&\s*Insights)?\b.*$",
            r"^\s*##\s+Synthesis and Insights\b.*$",
            r"^\s*##\s+综合(?:与)?洞察(?:\s|$|[:：-]).*$",
            r"^\s*##\s+综合(?:与)?洞察\s*$",
        ],
    },
    {
        "id": "limitations_caveats",
        "title": "Limitations & Caveats",
        "default_title": "局限性与注意事项",
        "default_heading": "## 局限性与注意事项",
        "aliases": (
            "Limitations & Caveats",
            "Limitations and Caveats",
            "局限性与注意事项",
            "局限性",
        ),
        "heading_patterns": [
            r"^\s*##\s+Limitations(?:\s*&\s*Caveats)?\b.*$",
            r"^\s*##\s+Limitations and Caveats\b.*$",
            r"^\s*##\s+局限性与注意事项(?:\s|$|[:：-]).*$",
            r"^\s*##\s+局限性与注意事项\s*$",
            r"^\s*##\s+局限性(?:\s|$|[:：-]).*$",
            r"^\s*##\s+局限性\s*$",
        ],
    },
    {
        "id": "recommendations",
        "title": "Recommendations",
        "default_title": "建议",
        "default_heading": "## 建议",
        "aliases": ("Recommendations", "建议"),
        "heading_patterns": [
            r"^\s*##\s+Recommendations\b.*$",
            r"^\s*##\s+建议(?:\s|$|[:：-]).*$",
            r"^\s*##\s+建议\s*$",
        ],
    },
    {
        "id": "bibliography",
        "title": "Bibliography",
        "default_title": "参考文献",
        "default_heading": "## 参考文献",
        "aliases": ("Bibliography", "参考文献", "参考资料"),
        "heading_patterns": [
            r"^\s*##\s+Bibliography\b.*$",
            r"^\s*##\s+参考文献(?:\s|$|[:：-]).*$",
            r"^\s*##\s+参考文献\s*$",
            r"^\s*##\s+参考资料(?:\s|$|[:：-]).*$",
            r"^\s*##\s+参考资料\s*$",
        ],
    },
    {
        "id": "methodology_appendix",
        "title": "Appendix: Methodology",
        "default_title": "附录：研究方法",
        "default_heading": "## 附录：研究方法",
        "aliases": (
            "Appendix: Methodology",
            "Methodology Appendix",
            "Methodology",
            "附录：研究方法",
            "附录：方法论",
            "研究方法附录",
            "研究方法",
        ),
        "heading_patterns": [
            r"^\s*##\s+Appendix:\s*Methodology\b.*$",
            r"^\s*##\s+Methodology Appendix\b.*$",
            r"^\s*##\s+Methodology\b.*$",
            r"^\s*##\s+附录[:：]\s*(?:研究方法|方法论)(?:\s|$|[:：-]).*$",
            r"^\s*##\s+附录[:：]\s*(?:研究方法|方法论)\s*$",
            r"^\s*##\s+研究方法附录(?:\s|$|[:：-]).*$",
            r"^\s*##\s+研究方法附录\s*$",
            r"^\s*##\s+研究方法(?:\s|$|[:：-]).*$",
            r"^\s*##\s+研究方法\s*$",
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

SECTION_ALIASES_BY_ID: Dict[str, Tuple[str, ...]] = {
    str(spec["id"]): tuple(str(alias) for alias in spec.get("aliases", (spec["title"],)))
    for spec in REPORT_SECTION_SPECS
}

SECTION_DEFAULT_TITLES_BY_ID: Dict[str, str] = {
    str(spec["id"]): str(spec.get("default_title", spec["title"]))
    for spec in REPORT_SECTION_SPECS
}

SECTION_DEFAULT_HEADINGS_BY_ID: Dict[str, str] = {
    str(spec["id"]): str(spec.get("default_heading", f"## {spec['title']}"))
    for spec in REPORT_SECTION_SPECS
}

SECTION_TITLES_BY_ID: Dict[str, str] = {
    str(spec["id"]): str(spec["title"])
    for spec in REPORT_SECTION_SPECS
}


def normalize_section_label(value: str) -> str:
    """Normalize a section label or markdown heading for alias matching."""
    stripped = re.sub(r"^\s*#+\s*", "", value).strip()
    return re.sub(r"\s+", " ", stripped).casefold()


def resolve_section_id(label: str) -> Optional[str]:
    """Resolve a canonical section id from an English or Chinese label."""
    normalized = normalize_section_label(label)
    for section_id, aliases in SECTION_ALIASES_BY_ID.items():
        if normalized in {normalize_section_label(alias) for alias in aliases}:
            return section_id

    heading_candidate = label.strip()
    if not heading_candidate.startswith("#"):
        heading_candidate = f"## {heading_candidate}"

    for spec in REPORT_SECTION_SPECS:
        if any(
            re.search(str(pattern), heading_candidate, re.MULTILINE | re.IGNORECASE)
            for pattern in spec["heading_patterns"]
        ):
            return str(spec["id"])

    return None


def get_section_spec(section_id: str) -> Dict[str, object]:
    """Return one report section spec by canonical id."""
    for spec in REPORT_SECTION_SPECS:
        if str(spec["id"]) == section_id:
            return spec
    raise KeyError(f"Unknown report section id: {section_id}")


def get_default_section_title(section_id: str) -> str:
    """Return the default visible section title for newly generated reports."""
    return SECTION_DEFAULT_TITLES_BY_ID[section_id]


def get_default_section_heading(section_id: str) -> str:
    """Return the default visible markdown heading for newly generated reports."""
    return SECTION_DEFAULT_HEADINGS_BY_ID[section_id]


def get_section_heading_patterns(section_id: str) -> Tuple[str, ...]:
    """Return regex patterns that match a top-level heading for one section."""
    return SECTION_PATTERNS_BY_ID[section_id]


def get_default_finding_heading(finding_number: int, title: str = "[标题]") -> str:
    """Return the default markdown heading for a numbered finding."""
    return f"### 发现 {finding_number}：{title}"


def get_finding_pattern(finding_number: int) -> str:
    """Return the regex that matches one numbered finding heading."""
    return (
        rf"^\s*###\s+(?:Finding|发现)\s+{finding_number}\s*"
        rf"(?:[:：-]\s*.*)?$"
    )


def get_any_finding_pattern() -> str:
    """Return the regex that matches any numbered finding heading."""
    return r"^\s*###\s+(?:Finding|发现)\s+(\d+)\s*(?:[:：-]\s*.*)?$"


def summarize_length_metrics(text: str) -> Dict[str, float]:
    """Compute length metrics that work for English, Chinese, and mixed text."""
    cjk_chars = len(CJK_CHAR_RE.findall(text))
    visible_chars = len(re.sub(r"\s+", "", text))
    word_count = len(WORD_RE.findall(text))
    sentence_units = len([item for item in SUMMARY_UNIT_RE.split(text) if item.strip()])
    bullet_units = len(SUMMARY_BULLET_RE.findall(text))
    summary_units = max(sentence_units, bullet_units)

    if summary_units == 0 and visible_chars > 0:
        summary_units = 1

    cjk_ratio = cjk_chars / max(visible_chars, 1)
    return {
        "cjk_chars": cjk_chars,
        "visible_chars": visible_chars,
        "word_count": word_count,
        "summary_units": summary_units,
        "cjk_ratio": cjk_ratio,
    }


def is_cjk_dominant(text: str, threshold: float = CJK_RATIO_THRESHOLD) -> bool:
    """Return whether a text block should use CJK-friendly length heuristics."""
    return summarize_length_metrics(text)["cjk_ratio"] >= threshold


def count_length_units(text: str) -> int:
    """Return a cross-language length approximation for progress tracking."""
    metrics = summarize_length_metrics(text)
    if metrics["cjk_ratio"] >= CJK_RATIO_THRESHOLD:
        return int(metrics["visible_chars"])
    return int(metrics["word_count"])


def min_length_for_section(min_words: int, text: str) -> int:
    """Return the completion threshold for a section body using language-aware units."""
    if is_cjk_dominant(text):
        return min_words * CJK_SECTION_CHAR_MULTIPLIER
    return min_words
