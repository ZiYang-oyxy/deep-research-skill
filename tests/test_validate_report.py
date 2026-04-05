import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from validate_report import ReportValidator  # noqa: E402


class ValidateReportTests(unittest.TestCase):
    def _write_report(self, directory: Path, content: str) -> Path:
        report_path = directory / "report.md"
        report_path.write_text(content, encoding="utf-8")
        return report_path

    def test_cjk_executive_summary_uses_character_based_validation(self):
        summary = (
            "## 执行摘要\n\n"
            "- 研究表明该领域在过去两年持续扩张，并且关键供应链瓶颈仍未完全缓解。[1]\n"
            "- 多数一手资料与行业报告结论一致，但在成本曲线和部署节奏上仍存在分歧。[2]\n"
            "- 对决策者而言，近期最重要的结论是先验证实施约束，再决定规模化路线。[3]\n"
        )
        report = "\n\n".join(
            [
                summary,
                "## 引言\n\n本报告说明研究范围、方法和关键假设。[1]",
                "## 主要分析\n\n### Finding 1: Test finding\n\n这里提供足够长的分析正文，用于满足主分析段落的存在性要求。[1][2]",
                "## 综合洞察\n\n跨来源比对后可以看到，需求侧信号强于供给侧兑现速度。[2]",
                "## 局限性与注意事项\n\n样本覆盖范围有限，部分指标口径并不完全一致。[2]",
                "## 建议\n\n建议先进行小范围试点，再扩大投资承诺。[3]",
                "## 参考文献\n\n[1] Source one\n[2] Source two\n[3] Source three",
                "## 附录：研究方法\n\n使用公开资料、官方文档与行业分析进行交叉验证。",
            ]
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            report_path = self._write_report(Path(temp_dir), report)
            validator = ReportValidator(report_path)
            self.assertTrue(validator._check_executive_summary(), validator.errors)

    def test_mixed_language_summary_passes_without_english_padding(self):
        summary = (
            "## 执行摘要\n\n"
            "这份摘要以中文为主，但保留 AI infrastructure、GPU supply 和 inference cost 等必要术语。[1]\n"
            "核心结论是：需求增长真实存在，不过商业化节奏取决于 energy availability 与 deployment readiness。[2]\n"
        )
        report = "\n\n".join(
            [
                summary,
                "## 引言\n\n说明研究目标与方法。[1]",
                "## 主要分析\n\n### Finding 1: Test finding\n\n分析内容已经写入，并包含多处引用。[1][2]",
                "## 综合洞察\n\n中英混合文本不应被误判为过短。[2]",
                "## 局限性\n\n部分英文术语无法自然翻译，因此保留原文。[2]",
                "## 建议\n\n建议保持术语原貌，同时允许中文标题结构。[2]",
                "## 参考文献\n\n[1] Source one\n[2] Source two",
                "## 研究方法\n\n通过多源交叉验证形成结论。",
            ]
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            report_path = self._write_report(Path(temp_dir), report)
            validator = ReportValidator(report_path)
            self.assertTrue(validator._check_executive_summary(), validator.errors)

    def test_required_sections_accept_chinese_headings(self):
        report = "\n\n".join(
            [
                "## 执行摘要\n\n这是一段足够长的中文摘要内容，用于通过中文长度校验，并说明主要结论与建议。[1]\n第二句补充关键限制与适用范围。[2]",
                "## 引言\n\n说明研究范围与方法。[1]",
                "## 主要分析\n\n### Finding 1: Test finding\n\n主体分析内容。[1][2]",
                "## 综合与洞察\n\n给出跨来源综合判断。[2]",
                "## 局限性与注意事项\n\n解释证据边界。[2]",
                "## 建议\n\n提出下一步行动建议。[2]",
                "## 参考资料\n\n[1] Source one\n[2] Source two",
                "## 研究方法附录\n\n说明检索和筛选方法。",
            ]
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            report_path = self._write_report(Path(temp_dir), report)
            validator = ReportValidator(report_path)
            self.assertTrue(validator._check_required_sections(), validator.errors)


if __name__ == "__main__":
    unittest.main()
