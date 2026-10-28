from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import common  # noqa: E402


def layout_for(root: Path, output: Path) -> common.ModuleLayout:
    return common.ModuleLayout(root, root / "preanalysis", None, {}, {}, output)


class StateV2MigrationTests(unittest.TestCase):
    def test_legacy_state_is_backed_up_and_old_session_is_not_reused(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "module"
            output = root / "test-points"
            (root / "preanalysis").mkdir(parents=True)
            output.mkdir(parents=True)
            path = output / "generation-state.json"
            legacy = {
                "schema_version": 3,
                "module_dir": root.as_posix(),
                "preanalysis_dir": (root / "preanalysis").as_posix(),
                "manifest_path": None,
                "manifest_sha256": None,
                "output_dir": output.as_posix(),
                "session_id": "legacy-resume-thread",
                "rsus": [{"rsu_id": "RSU-001", "generation_status": "pending"}],
            }
            path.write_text(json.dumps(legacy), encoding="utf-8")

            migrated = common.load_state(output, layout_for(root, output))

            assert migrated is not None
            self.assertEqual(migrated["schema_version"], 4)
            self.assertEqual(migrated["scheduler_schema"], "rsu-test-point-generation/state-v2")
            self.assertEqual(migrated["migrated_from_schema"], 3)
            self.assertEqual(migrated["foundation"]["status"], "pending")
            self.assertIsNone(migrated["foundation"]["thread_id"])
            backup = output / migrated["migration_backup"]
            self.assertTrue(backup.is_file())
            self.assertIn("legacy-resume-thread", backup.read_text(encoding="utf-8"))

    def test_corrupt_and_unknown_state_are_rejected_without_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "module"
            output = root / "test-points"
            (root / "preanalysis").mkdir(parents=True)
            output.mkdir(parents=True)
            path = output / "generation-state.json"
            for value, pattern in (("{broken", "invalid generation state JSON"), ('{"schema_version":99}', "unsupported")):
                path.write_text(value, encoding="utf-8")
                before = path.read_bytes()
                with self.assertRaisesRegex(common.WorkflowError, pattern):
                    common.load_state(output, layout_for(root, output))
                self.assertEqual(path.read_bytes(), before)

    def test_atomic_write_never_leaves_temp_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "state.json"
            common.atomic_write_json(path, {"schema_version": 4, "value": 1})
            common.atomic_write_json(path, {"schema_version": 4, "value": 2})
            self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["value"], 2)
            self.assertEqual(list(path.parent.glob("*.tmp")), [])


if __name__ == "__main__":
    unittest.main()
