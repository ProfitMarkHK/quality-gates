"""Regression tests for the hermetic operator-env guard in tests/conftest.py.

Runs the real conftest in a child pytest process with QUALITY_GATES_LLM_*
exported, so the guard is exercised exactly as a developer's shell would
trigger it. Unit-test modules must see no operator LLM vars regardless of
the live opt-in flag; the live module must keep them.
"""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

CONFTEST = Path(__file__).resolve().parent / "conftest.py"

OPERATOR_ENV = {
    "QUALITY_GATES_LLM_ENABLED": "1",
    "QUALITY_GATES_LLM_ENDPOINT": "http://127.0.0.1:9/v1/chat/completions",
    "QUALITY_GATES_LLM_EXCLUDE_PATTERNS": "**/*.pyc",
}

UNIT_PROBE = """
import os

def test_operator_env_is_stripped():
    leaked = sorted(k for k in os.environ if k.startswith("QUALITY_GATES_LLM_"))
    assert leaked == []
"""

LIVE_PROBE = """
import os

def test_operator_env_is_preserved():
    assert os.environ.get("QUALITY_GATES_LLM_ENABLED") == "1"
    assert os.environ.get("QUALITY_GATES_LLM_EXCLUDE_PATTERNS") == "**/*.pyc"
"""


class HermeticOperatorEnvTests(unittest.TestCase):
    def _run_probes(self, live_flag):
        with tempfile.TemporaryDirectory() as tmp:
            shutil.copy(CONFTEST, Path(tmp) / "conftest.py")
            (Path(tmp) / "test_unit_probe.py").write_text(UNIT_PROBE, encoding="utf-8")
            (Path(tmp) / "test_llm_assessment_live.py").write_text(
                LIVE_PROBE, encoding="utf-8"
            )
            env = {
                k: v
                for k, v in os.environ.items()
                if not k.startswith("QUALITY_GATES_")
            }
            env.update(OPERATOR_ENV)
            if live_flag is not None:
                env["QUALITY_GATES_LIVE_SMOKE"] = live_flag
            return subprocess.run(
                [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", tmp],
                cwd=tmp,
                env=env,
                capture_output=True,
                text=True,
                timeout=120,
            )

    def test_guard_strips_unit_env_and_preserves_live_env(self):
        for live_flag in (None, "0", "1"):
            with self.subTest(QUALITY_GATES_LIVE_SMOKE=live_flag):
                proc = self._run_probes(live_flag)
                self.assertEqual(
                    proc.returncode, 0, proc.stdout + proc.stderr
                )
                self.assertIn("2 passed", proc.stdout)


if __name__ == "__main__":
    unittest.main()
