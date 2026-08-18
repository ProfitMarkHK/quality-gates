import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "skill" / "quality-gates" / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from detect_project import detect, summarize  # noqa: E402


class DetectPowerShellTests(unittest.TestCase):
    def test_detects_powershell_sources_and_analyzer_settings(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "install.ps1").write_text("Write-Output 'ok'\n", encoding="utf-8")
            (root / "module.psm1").write_text("function Get-Thing {}\n", encoding="utf-8")
            (root / "PSScriptAnalyzerSettings.psd1").write_text(
                "@{ ExcludeRules = @() }\n", encoding="utf-8"
            )

            report = detect(root)

        self.assertEqual(report["languages"], ["PowerShell"])
        self.assertEqual(report["language_file_counts"]["PowerShell"], 3)
        self.assertIn("PSScriptAnalyzer", report["linters"])
        self.assertTrue(report["linters"]["PSScriptAnalyzer"]["config_files"])
        self.assertIn("Invoke-ScriptAnalyzer", report["linters"]["PSScriptAnalyzer"]["note"])
        self.assertIn("Invoke-ScriptAnalyzer", summarize(report))

    def test_detects_invoke_script_analyzer_in_gate_script(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            scripts = root / "scripts"
            scripts.mkdir()
            (scripts / "check.ps1").write_text(
                "Invoke-ScriptAnalyzer -Path install.ps1\n",
                encoding="utf-8",
            )

            report = detect(root)

        self.assertIn("PSScriptAnalyzer", report["linters"])
        self.assertTrue(report["linters"]["PSScriptAnalyzer"]["in_build_or_ci"])
        self.assertEqual(
            report["existing_gate_runner"],
            {"type": "script", "path": "scripts/check.ps1"},
        )

    def test_warns_when_settings_exist_without_analyzer_invocation(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "PSScriptAnalyzerSettings.psd1").write_text(
                "@{ ExcludeRules = @() }\n", encoding="utf-8"
            )

            report = detect(root)

        analyzer = report["linters"]["PSScriptAnalyzer"]
        self.assertTrue(analyzer["config_files"])
        self.assertFalse(analyzer["in_build_or_ci"])
        self.assertIn("Invoke-ScriptAnalyzer", analyzer["note"])

    def test_detects_non_settings_psd1_as_powershell(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "module-data.psd1").write_text("@{ Name = 'demo' }\n", encoding="utf-8")

            report = detect(root)

        self.assertEqual(report["languages"], ["PowerShell"])
        self.assertEqual(report["language_file_counts"]["PowerShell"], 1)
        self.assertIn("PSScriptAnalyzer (candidate)", report["linters"])

    def test_reports_missing_powershell_linter_as_a_candidate(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "install.ps1").write_text("Write-Output 'ok'\n", encoding="utf-8")

            report = detect(root)

        self.assertIn("PSScriptAnalyzer (candidate)", report["linters"])
        self.assertIn("PowerShell", report["linters"]["PSScriptAnalyzer (candidate)"]["note"])


if __name__ == "__main__":
    unittest.main()
