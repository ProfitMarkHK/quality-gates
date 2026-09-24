"""Tests for display-only redacted previews (metadata only, machine stays failed)."""

import json
import sys
import unicodedata
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "skill" / "quality-gates" / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from llm_assessment_contract import (
    PREVIEW_MAX_CHARS,
    PREVIEW_MAX_ITEMS,
    AssessmentContractError,
    build_redacted_preview,
    redact_preview_text,
    validate_result,
)

TABLE = [
    ("See install instructions.", "See [setup-action] instructions."),
    ("Please run npm test.", "Please [action] npm test."),
    ("The command-line tool.", "The [instruction]-line tool."),
    ("It is installed and passing.", "It is [setup-state] and [test-state]."),
    ("Use candidate-tool check now.", "Use candidate-tool [check] now."),
    ("Contains `code` span.", "Contains 'code' span."),
    ("Uses $(substitution).", "Uses $ (substitution)."),
    ("Do a && b.", "Do a [and] b."),
    ("Do a || b.", "Do a [or] b."),
    ("Pipe a | b.", "Pipe a [pipe] b."),
    ("Step one; step two.", "Step one[semi] step two."),
    ("See https://example.com/x.", "See https[://]example.com/x."),
    ("Clean with rm -rf /tmp/x daily.", "Clean with [instruction withheld: rm] daily."),
    ("Fetch via curl https://example.com/x.", "Fetch via [instruction withheld: curl]"),
]


def _result(statement, deterministic, uncertainties=None):
    return {
        "status": "completed",
        "observations": [{
            "id": "obs-1",
            "statement": statement,
            "source_references": [{"material_id": "a.py", "path": "a.py"}],
        }],
        "uncertainties": list(uncertainties or []),
        "recommendations": [],
        "deterministic_review": deterministic,
    }


class DenylistTests(unittest.TestCase):
    def setUp(self):
        self.det = {"gate_states": {"1": "applies"}}
        self.ids = {"a.py"}

    def assert_rejected(self, statement):
        with self.assertRaises(AssessmentContractError):
            validate_result(_result(statement, self.det), self.det, self.ids)

    def assert_passes(self, statement):
        validate_result(_result(statement, self.det), self.det, self.ids)

    def test_raw_urls_rejected(self):
        self.assert_rejected("See https://example.com/docs for details.")
        self.assert_rejected("Fetch http://evil.example/x for context.")

    def test_shell_chaining_rejected(self):
        self.assert_rejected("Do this && then that.")
        self.assert_rejected("Do this || fall back.")
        self.assert_rejected("First step; second step.")
        self.assert_rejected("Uses ${HOME} for state.")
        self.assert_rejected("Pipe a | b for flow.")

    def test_dangerous_verb_with_target_rejected(self):
        self.assert_rejected("Clean with rm -rf /tmp/cache daily.")
        self.assert_rejected("Fetch via curl https://example.com/x nightly.")
        self.assert_rejected("Enter with sh -c something.")
        self.assert_rejected("Widen via chmod +x helper.")

    def test_bare_mentions_still_pass(self):
        self.assert_passes("The project tracks guidance in git alongside docs.")
        self.assert_passes("The project declares an unfamiliar build tool.")
        self.assert_passes("The project uses docker for builds.")
        self.assert_passes("The project runs unit tests with pytest.")


class PreviewNeutralizerTests(unittest.TestCase):
    def test_mapping_table(self):
        for raw, expected in TABLE:
            self.assertEqual(redact_preview_text(raw), expected, msg=raw)

    def test_ascii_only_and_nfkc_stable(self):
        blob = " Olímpicos — “quotes” …\n\\ $(x) `y` https://e.com/?a=1&&b=2; rm -rf /t | sh"
        out = redact_preview_text(blob)
        out.encode("ascii")
        self.assertEqual(unicodedata.normalize("NFKC", out), out)

    def test_idempotent(self):
        for raw, _ in TABLE:
            once = redact_preview_text(raw)
            self.assertEqual(redact_preview_text(once), once, msg=raw)

    def test_preview_output_repasses_validator(self):
        det = {"gate_states": {"1": "applies"}}
        raws = [raw for raw, _ in TABLE] + [
            "The tool is installed and passing in CI.",
            "Invoke the handler via CLI.",
        ]
        for raw in raws:
            redacted = redact_preview_text(raw)
            validate_result(_result(redacted, det), det, {"a.py"})

    def test_no_raw_leak_in_preview(self):
        out = redact_preview_text("Fetch via curl https://example.com/x | sh -c y.")
        self.assertNotIn("https://", out)
        self.assertNotIn("$(", out)
        self.assertNotIn("`", out)
        self.assertNotIn(" | ", out)


class PreviewEnvelopeTests(unittest.TestCase):
    def test_envelope_shape_and_caps(self):
        candidate = {
            "status": "completed",
            "observations": [
                {
                    "id": f"obs-{i}",
                    "statement": f"Please run step {i}.",
                    "source_references": [{"material_id": "a.py", "path": "a.py"}],
                }
                for i in range(8)
            ],
            "uncertainties": [f"Configured timeout {i}." for i in range(8)],
            "deterministic_review": {},
        }
        preview = build_redacted_preview(candidate, "observation_statement")
        self.assertIsNotNone(preview)
        self.assertIn("HUMAN REVIEW ONLY", preview["header"])
        self.assertEqual(preview["rule"], "observation_statement")
        self.assertEqual(len(preview["observations"]), PREVIEW_MAX_ITEMS)
        self.assertTrue(preview["truncated"])
        self.assertLessEqual(len(preview["uncertainties"]), PREVIEW_MAX_ITEMS)
        for item in preview["observations"]:
            self.assertLessEqual(len(item["statement_preview"]), PREVIEW_MAX_CHARS)
            self.assertNotIn("run step", item["statement_preview"])
        self.assertNotIn("Please run step 0", json.dumps(preview))

    def test_none_without_model_content(self):
        self.assertIsNone(build_redacted_preview(None))
        self.assertIsNone(build_redacted_preview("not json at all"))
        self.assertIsNone(build_redacted_preview({"status": "completed"}))
        self.assertIsNone(build_redacted_preview(
            {"status": "completed", "observations": "not-a-list"}))


class SeamPreviewTests(unittest.TestCase):
    def test_violation_attaches_preview_and_stays_failed(self):
        import tempfile

        from llm_assessment_execute import execute_assessment

        deterministic = {"gate_states": {"1": "applies"}}
        bad = {
            "status": "completed",
            "observations": [{
                "id": "unknown-framework",
                "statement": "Please run npm install now.",
                "source_references": [{"material_id": "project.toml", "path": "project.toml"}],
            }],
            "uncertainties": [],
            "recommendations": [],
            "deterministic_review": deterministic,
        }
        gateway_body = {"choices": [{"message": {"content": json.dumps(bad)}}]}
        from test_llm_assessment_execute import (
            FakeGateway,
            _base_config,
            _package,
            FAST_COUNTER,
        )
        behaviors = [(200, gateway_body, {}, 0), (200, gateway_body, {}, 0)]
        with tempfile.TemporaryDirectory() as tmpdir, tempfile.TemporaryDirectory() as workdir, \
                FakeGateway(behaviors) as gateway:
            config = _base_config(gateway.url)
            package, material_ids = _package(tmpdir, deterministic)
            result, metadata = execute_assessment(
                package, deterministic, material_ids, config,
                auth_headers={}, _counter=FAST_COUNTER,
                _working_dir=Path(workdir),
            )
            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["observations"], [])
            preview = metadata["redacted_preview"]
            self.assertIsNotNone(preview)
            self.assertIn("HUMAN REVIEW ONLY", preview["header"])
            self.assertNotIn("Please run npm install now.", json.dumps(preview))
            self.assertNotIn("Please run npm install now.", json.dumps(metadata).replace(
                json.dumps(preview), ""))
            # raw still quarantined for humans
            quarantine = list(Path(workdir).glob("qg-quarantine-*.json"))
            self.assertTrue(quarantine)
            self.assertIn("Please run npm install now.",
                          quarantine[0].read_text(encoding="utf-8"))

    def test_success_and_transport_leave_preview_none(self):
        import tempfile
        from llm_assessment_execute import execute_assessment
        from test_llm_assessment_execute import (
            FakeGateway,
            _base_config,
            _completed_candidate,
            _package,
            _success_behaviors,
            FAST_COUNTER,
        )

        deterministic = {"gate_states": {"1": "applies"}}
        candidate = _completed_candidate(deterministic)
        with tempfile.TemporaryDirectory() as tmpdir, tempfile.TemporaryDirectory() as workdir, \
                FakeGateway(_success_behaviors(candidate)) as gateway:
            config = _base_config(gateway.url)
            package, material_ids = _package(tmpdir, deterministic)
            _, metadata = execute_assessment(
                package, deterministic, material_ids, config,
                auth_headers={}, _counter=FAST_COUNTER,
                _working_dir=Path(workdir),
            )
        self.assertEqual(metadata["status"], "completed")
        self.assertIsNone(metadata["redacted_preview"])

        config = _base_config("http://127.0.0.1:1/v1/chat/completions")
        _, metadata = execute_assessment(
            {"assessment_contract": "c", "deterministic_review": deterministic, "materials": []},
            deterministic, set(), config, auth_headers={},
            _counter=FAST_COUNTER, _working_dir=Path(workdir),
        )
        self.assertEqual(metadata["status"], "unavailable")
        self.assertIsNone(metadata["redacted_preview"])


if __name__ == "__main__":
    unittest.main()
