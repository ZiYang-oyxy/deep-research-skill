import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from verify_citations import CitationVerifier  # noqa: E402


class OutputLocalizationTests(unittest.TestCase):
    def test_verify_citations_accepts_chinese_bibliography_heading_and_quotes(self):
        report = "\n\n".join(
            [
                "## 执行摘要\n\n中文摘要引用了来源。[1]",
                "## 参考文献\n\n[1] 示例机构（2026）。《中文标题示例》。示例发布方。https://example.com/source",
            ]
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            report_path = Path(temp_dir) / "report.md"
            report_path.write_text(report, encoding="utf-8")
            verifier = CitationVerifier(report_path)
            entries = verifier.extract_bibliography()

            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0]["num"], "1")
            self.assertEqual(entries[0]["title"], "中文标题示例")
            self.assertEqual(entries[0]["url"], "https://example.com/source")

if __name__ == "__main__":
    unittest.main()
