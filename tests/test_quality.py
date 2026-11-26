import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "quality", Path(__file__).resolve().parents[1] / "template/management/quality.py")
quality = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(quality)


class QualityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        (self.root / "management").mkdir()
        (self.root / "30-work").mkdir()

    def config(self, steps):
        (self.root / quality.CONFIG).write_text(
            json.dumps({"schemaVersion": 1, "steps": steps}), encoding="utf-8")

    def step(self, name, tier, code):
        return {"name": name, "level": tier, "cwd": "30-work",
                "argv": [sys.executable, "-c", code], "timeout": 15}

    def test_unconfigured_is_not_pass(self):
        result, code = quality.run(self.root, "quick", True)
        self.assertEqual((result["status"], code), ("incomplete", 2))

    def test_plan_does_not_execute(self):
        self.config([self.step("write", "quick", "open('marker','w').close()")])
        self.assertEqual(quality.run(self.root, "quick")[0]["status"], "plan")
        self.assertFalse((self.root / "30-work/marker").exists())

    def test_quick_does_not_run_verify(self):
        self.config([self.step("ok", "quick", "print('success')"),
                     self.step("fail", "verify", "raise SystemExit(7)")])
        result, code = quality.run(self.root, "quick", True)
        self.assertEqual((result["status"], code), ("pass", 0))
        self.assertNotIn("tail", result["steps"][0])

    def test_fail_stops_and_output_is_bounded(self):
        self.config([self.step("fail", "quick", "print('x'*10000); raise SystemExit(7)"),
                     self.step("later", "quick", "raise AssertionError()")])
        result, code = quality.run(self.root, "quick", True)
        self.assertEqual(code, 1)
        self.assertEqual(result["notRun"], ["later"])
        self.assertTrue(result["steps"][0]["truncated"])
        self.assertLessEqual(len(result["steps"][0]["tail"]), quality.TAIL_BYTES)

    def test_missing_release_is_incomplete(self):
        self.config([self.step("ok", "quick", "pass"), self.step("v", "verify", "pass")])
        result, code = quality.run(self.root, "release", True)
        self.assertEqual(code, 2)
        self.assertEqual(result["missingLevels"], ["release"])

    def test_traversal_rejected(self):
        step = self.step("bad", "quick", "pass")
        step["cwd"] = "../"
        self.config([step])
        with self.assertRaises(ValueError):
            quality.run(self.root, "quick")


if __name__ == "__main__":
    unittest.main()
