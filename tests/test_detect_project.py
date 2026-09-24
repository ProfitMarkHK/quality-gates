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


class DetectAgentSkillTests(unittest.TestCase):
    def test_detects_root_and_nested_agent_skills(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "SKILL.md").write_text(
                "---\nname: example\ndescription: Example\n---\n",
                encoding="utf-8",
            )
            nested = root / "skills" / "nested-skill"
            nested.mkdir(parents=True)
            (nested / "SKILL.md").write_text(
                "---\nname: nested-skill\ndescription: Nested\n---\n",
                encoding="utf-8",
            )

            report = detect(root)

        self.assertEqual(
            report["agent_skills"],
            [
                {"directory": ".", "file": "SKILL.md"},
                {"directory": "skills/nested-skill", "file": "skills/nested-skill/SKILL.md"},
            ],
        )
        self.assertIn("Agent skills", summarize(report))


class DetectComplexityTests(unittest.TestCase):
    def test_detects_ruff_c901_via_pyproject(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "app.py").write_text("def f():\n    pass\n", encoding="utf-8")
            (root / "pyproject.toml").write_text(
                "[tool.ruff.lint.mccabe]\nmax-complexity = 10\n"
                "[tool.ruff.lint]\nselect = [\"C901\"]\n",
                encoding="utf-8",
            )

            report = detect(root)

        self.assertIn("ruff-C901", report["complexity"])
        self.assertTrue(report["complexity"]["ruff-C901"]["in_pyproject"])
        self.assertIn("Complexity", summarize(report))

    def test_detects_xenon_via_runner_invocation(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "app.py").write_text("def f():\n    pass\n", encoding="utf-8")
            (root / "Makefile").write_text(
                "check:\n\txenon --max-absolute B src/\n",
                encoding="utf-8",
            )

            report = detect(root)

        self.assertIn("xenon", report["complexity"])
        self.assertTrue(report["complexity"]["xenon"]["in_build_or_ci"])

    def test_reports_candidate_when_python_has_no_complexity_wiring(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "app.py").write_text("def f():\n    pass\n", encoding="utf-8")

            report = detect(root)

        self.assertIn("ruff-C901/xenon (candidate)", report["complexity"])
        self.assertIn("C901", report["complexity"]["ruff-C901/xenon (candidate)"]["note"])

    def test_detects_eslint_complexity_rule(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "app.ts").write_text("export const f = () => 1;\n", encoding="utf-8")
            (root / "eslint.config.js").write_text(
                "export default [{ rules: { complexity: ['error', 10] } }];\n",
                encoding="utf-8",
            )

            report = detect(root)

        self.assertIn("eslint-complexity", report["complexity"])

    def test_no_complexity_candidate_for_prose_only_repo(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "README.md").write_text("# docs\n", encoding="utf-8")

            report = detect(root)

        self.assertEqual(report["complexity"], {})
        self.assertIn("Complexity", summarize(report))


if __name__ == "__main__":
    unittest.main()
