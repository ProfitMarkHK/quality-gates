"""Self-describing quarantine envelopes and the display-only reader (AIDEV-547)."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "skill" / "quality-gates" / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from llm_assessment_contract import build_offending_items  # noqa: E402
from llm_assessment_execute import _quarantine_write  # noqa: E402

# Reuse the gateway harness from the execute suite (same package, stdlib).
sys.path.insert(0, str(ROOT / "tests"))
from test_llm_assessment_execute import (  # noqa: E402
    FAST_COUNTER,
    FakeGateway,
    _base_config,
    _package,
    _success_behaviors,
    execute_assessment,
)

READER = SCRIPT_DIR / "quarantine_read.py"


def _candidate(deterministic, statements=("Clean remark about layout.",)):
    observations = []
    for i, statement in enumerate(statements):
        observations.append({
            "id": f"obs-{i + 1}",
            "statement": statement,
            "source_references": [{"material_id": "project.toml", "path": "project.toml"}],
        })
    return {
        "status": "completed",
        "observations": observations,
        "uncertainties": [],
        "recommendations": [],
        "deterministic_review": deterministic,
    }


class OffendingItemsTests(unittest.TestCase):
    def test_matching_observation_id_wins_over_siblings(self):
        deterministic = {"gate_states": {"1": "applies"}}
        candidate = _candidate(deterministic, ("First remark.", "Second remark."))
        items = build_offending_items(candidate, "observation_statement", "obs-2")
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["kind"], "observation")
        self.assertEqual(items[0]["id"], "obs-2")
        self.assertIn("Second remark", items[0]["text_preview"])

    def test_unknown_id_yields_nothing(self):
        candidate = _candidate({"gate_states": {}})
        self.assertEqual(build_offending_items(candidate, "observation_statement", "obs-9"), [])

    def test_uncertainty_rule_lists_uncertainties(self):
        candidate = _candidate({"gate_states": {}})
        candidate["observations"] = []
        candidate["uncertainties"] = ["First open question.", "Second open question."]
        items = build_offending_items(candidate, "uncertainty_text", "")
        self.assertEqual(len(items), 2)
        self.assertTrue(all(item["kind"] == "uncertainty" for item in items))
        self.assertIn("First open question", items[0]["text_preview"])

    def test_non_dict_candidate_yields_nothing(self):
        self.assertEqual(build_offending_items("not a dict", "observation_statement", "obs-1"), [])
        self.assertEqual(build_offending_items(None, "", ""), [])


class EnrichedEnvelopeTests(unittest.TestCase):
    def test_summary_keys_precede_raw_text_and_raw_is_identical(self):
        import tempfile

        deterministic = {"gate_states": {"1": "applies"}}
        raw = json.dumps(_candidate(deterministic))
        with tempfile.TemporaryDirectory() as workdir:
            path = _quarantine_write(
                raw, "observation_statement", "obs-1", Path(workdir),
                candidate=json.loads(raw), deterministic_review=deterministic,
            )
            envelope = json.loads(Path(path).read_text(encoding="utf-8"))
        keys = list(envelope.keys())
        for key in ("echo", "offending", "redacted_preview"):
            self.assertIn(key, keys)
            self.assertLess(keys.index(key), keys.index("raw_text"))
        self.assertEqual(envelope["raw_text"], raw)
        self.assertTrue(envelope["echo"]["identical"])
        self.assertGreater(envelope["echo"]["bytes"], 0)
        self.assertEqual(len(envelope["offending"]), 1)
        self.assertEqual(envelope["offending"][0]["id"], "obs-1")

    def test_mismatched_echo_reports_not_identical(self):
        import tempfile

        deterministic = {"gate_states": {"1": "applies"}}
        candidate = _candidate({"gate_states": {"1": "gap"}})
        raw = json.dumps(candidate)
        with tempfile.TemporaryDirectory() as workdir:
            path = _quarantine_write(
                raw, "observation_statement", "obs-1", Path(workdir),
                candidate=candidate, deterministic_review=deterministic,
            )
            envelope = json.loads(Path(path).read_text(encoding="utf-8"))
        self.assertFalse(envelope["echo"]["identical"])

    def test_unparsable_output_nulls_summaries_and_keeps_raw(self):
        import tempfile

        raw = '{"status": "complet'
        with tempfile.TemporaryDirectory() as workdir:
            path = _quarantine_write(raw, None, None, Path(workdir))
            envelope = json.loads(Path(path).read_text(encoding="utf-8"))
        self.assertIsNone(envelope["echo"])
        self.assertIsNone(envelope["offending"])
        self.assertIsNone(envelope["redacted_preview"])
        self.assertEqual(envelope["raw_text"], raw)


class FailingRunEnvelopeTests(unittest.TestCase):
    def test_failing_run_quarantine_is_self_describing(self):
        import tempfile

        deterministic = {"gate_states": {"1": "applies"}}
        bad = _candidate(deterministic, ("First remark.", "run the checks now"))
        bad["observations"][1]["source_references"] = [
            {"material_id": "project.toml", "path": "project.toml"}
        ]
        sent = json.dumps(bad)
        with tempfile.TemporaryDirectory() as tmpdir, tempfile.TemporaryDirectory() as workdir, \
                FakeGateway(_success_behaviors(bad)) as gateway:
            config = _base_config(gateway.url)
            package, material_ids = _package(tmpdir, deterministic)
            result, metadata = execute_assessment(
                package, deterministic, material_ids, config,
                auth_headers={}, _counter=FAST_COUNTER,
                _working_dir=Path(workdir),
            )
            self.assertEqual(result["status"], "failed")
            files = list((Path(workdir) / "quarantine").glob("qg-quarantine-*.json"))
            self.assertEqual(len(files), 1)
            envelope = json.loads(files[0].read_text(encoding="utf-8"))
        self.assertEqual(envelope["raw_text"], sent)
        self.assertTrue(envelope["echo"]["identical"])
        self.assertEqual(
            [item["id"] for item in envelope["offending"] if item["kind"] == "observation"],
            ["obs-2"],
        )


class ReaderScriptTests(unittest.TestCase):
    def _write_envelope(self, directory, name, violation, raw_text):
        path = Path(directory) / name
        path.write_text(json.dumps({
            "header": "HUMAN REVIEW ONLY test",
            "violation": violation,
            "raw_text": raw_text,
        }), encoding="utf-8")
        return path

    def test_reader_flags_failing_observation_without_echo_bulk(self):
        deterministic = {"gate_states": {"1": "applies"}}
        echo_bulk = "ECHO-BULK-SENTINEL " * 500
        candidate = _candidate({**deterministic, "bulk": echo_bulk})
        with tempfile.TemporaryDirectory() as tmpdir:
            target = self._write_envelope(
                tmpdir, "new.json",
                {"observation_id": "obs-1", "rule": "observation_statement"},
                json.dumps(candidate),
            )
            proc = subprocess.run(
                [sys.executable, str(READER), str(target)],
                capture_output=True, text=True, timeout=60,
            )
        self.assertEqual(proc.returncode, 0)
        self.assertIn("FLAGGED", proc.stdout)
        self.assertIn("obs-1", proc.stdout)
        self.assertNotIn("ECHO-BULK-SENTINEL", proc.stdout)

    def test_reader_handles_legacy_envelope_without_new_keys(self):
        deterministic = {"gate_states": {"1": "applies"}}
        candidate = _candidate(deterministic)
        candidate.pop("deterministic_review")
        with tempfile.TemporaryDirectory() as tmpdir:
            target = self._write_envelope(
                tmpdir, "legacy.json",
                {"observation_id": "", "rule": "uncertainty_text"},
                json.dumps(candidate),
            )
            proc = subprocess.run(
                [sys.executable, str(READER), str(target)],
                capture_output=True, text=True, timeout=60,
            )
        self.assertEqual(proc.returncode, 0)
        self.assertIn("uncertainty_text", proc.stdout)
        self.assertIn("MISSING", proc.stdout)

    def test_reader_reports_unparsable_instead_of_crashing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            target = self._write_envelope(
                tmpdir, "broken.json",
                {"observation_id": "", "rule": ""},
                '{"status": "complet',
            )
            proc = subprocess.run(
                [sys.executable, str(READER), str(target)],
                capture_output=True, text=True, timeout=60,
            )
        self.assertEqual(proc.returncode, 0)
        self.assertIn("UNPARSABLE", proc.stdout)


if __name__ == "__main__":
    unittest.main()
