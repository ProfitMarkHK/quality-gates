"""Opt-in live smoke test against the approved LLM gateway.

Skipped unless QUALITY_GATES_LIVE_SMOKE=1 with a fully configured operator
environment (QUALITY_GATES_LLM_ENABLED=1 and QUALITY_GATES_LLM_ENDPOINT).
Reads no secrets from the repo: every gateway setting comes from process
env (a local .env outside the target, never committed). Uses a tiny
synthetic target so the run stays cheap, and asserts the seam contract:
a completed/partial assessment that echoes the deterministic review
unchanged with source-backed observations.
"""

import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "skill" / "quality-gates" / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from llm_assessment_contract import build_input_package  # noqa: E402
from llm_assessment_execute import execute_assessment, load_config  # noqa: E402


def _live_opt_in():
    return os.environ.get("QUALITY_GATES_LIVE_SMOKE") == "1"


@unittest.skipUnless(
    _live_opt_in(),
    "live gateway smoke test: set QUALITY_GATES_LIVE_SMOKE=1 with operator "
    "QUALITY_GATES_LLM_* env configured",
)
class LiveGatewaySmokeTests(unittest.TestCase):
    def test_live_assessment_completes_and_preserves_deterministic_review(self):
        config = load_config()
        self.assertTrue(config["enabled"], "operator env must enable the assessment")
        self.assertTrue(config["endpoint"], "operator env must provide an endpoint")

        target = Path(self._tmp_target())
        target.mkdir(parents=True, exist_ok=True)
        (target / "README.md").write_text(
            "# sample-service\n\nA tiny Python service.\n", encoding="utf-8"
        )
        (target / "service.conf").write_text(
            "[runtime]\nframework = frobnicate\nbuilder = muddle\n",
            encoding="utf-8",
        )
        deterministic = {"gate_states": {"1": "applies", "7": "no-op"}}

        package = build_input_package(
            target, deterministic, config.get("exclude_patterns", [])
        )
        self.assertTrue(package["materials"], "smoke target must yield materials")
        material_ids = {item["material_id"] for item in package["materials"]}

        result, metadata = execute_assessment(
            package, deterministic, material_ids, config
        )
        self.assertIn(
            result["status"],
            ("completed", "partial"),
            f"live assessment did not complete: {result.get('status')}",
        )
        self.assertEqual(result["deterministic_review"], deterministic)
        for obs in result.get("observations", []):
            refs = obs.get("source_references", [])
            self.assertTrue(refs, f"observation {obs.get('id')} lacks source references")
            for ref in refs:
                self.assertIn(ref["material_id"], material_ids)

    def _tmp_target(self):
        base = Path(os.environ.get("TMPDIR", "/tmp")) / "qg-live-smoke-target"
        for child in sorted(base.glob("*")) if base.exists() else []:
            if child.is_file():
                child.unlink()
        return str(base)
