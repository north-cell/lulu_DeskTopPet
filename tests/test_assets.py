import json
import tempfile
import unittest
from pathlib import Path

from lulu_pet.assets import AssetManager
from lulu_pet.paths import resource_path


class AssetManagerTests(unittest.TestCase):
    def test_manifest_loads_actions_and_lines(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "idle.svg").write_text("<svg />", encoding="utf-8")
            manifest = {
                "default_action": "idle",
                "actions": {
                    "idle": {
                        "file": "idle.svg",
                        "duration_ms": 3000,
                        "weight": 3,
                        "lines": ["噜噜在发呆。"],
                    }
                },
            }
            (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

            manager = AssetManager(root / "manifest.json")
            action = manager.get_action("idle")

            self.assertEqual(action.name, "idle")
            self.assertEqual(action.duration_ms, 3000)
            self.assertEqual(action.weight, 3)
            self.assertEqual(action.lines, ("噜噜在发呆。",))
            self.assertEqual(action.file_path, root / "idle.svg")

    def test_missing_manifest_uses_builtin_placeholder_actions(self):
        with tempfile.TemporaryDirectory() as tmp:
            manager = AssetManager(Path(tmp) / "missing.json")

            self.assertEqual(manager.default_action, "idle")
            self.assertIn("clicked", manager.action_names)
            self.assertGreater(manager.get_action("idle").weight, 0)

    def test_weighted_random_action_uses_available_actions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "manifest.json").write_text(
                json.dumps(
                    {
                        "default_action": "idle",
                        "actions": {
                            "idle": {"file": "missing.svg", "duration_ms": 100, "weight": 1, "lines": []},
                            "happy": {"file": "missing.svg", "duration_ms": 100, "weight": 20, "lines": []},
                        },
                    }
                ),
                encoding="utf-8",
            )
            manager = AssetManager(root / "manifest.json")

            selected = {manager.random_action_name() for _ in range(50)}

            self.assertTrue(selected.issubset({"idle", "happy"}))
            self.assertIn("happy", selected)

    def test_manifest_action_supports_multiple_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ("a.webp", "b.webp", "c.webp"):
                (root / name).write_bytes(b"image")
            (root / "manifest.json").write_text(
                json.dumps(
                    {
                        "default_action": "idle",
                        "actions": {
                            "idle": {
                                "files": ["a.webp", "b.webp", "c.webp"],
                                "duration_ms": 100,
                                "weight": 1,
                                "lines": [],
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            manager = AssetManager(root / "manifest.json")

            action = manager.get_action("idle")

            self.assertEqual(action.file_paths, (root / "a.webp", root / "b.webp", root / "c.webp"))
            self.assertIn(action.file_path, action.file_paths)

    def test_random_file_path_uses_all_action_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "manifest.json").write_text(
                json.dumps(
                    {
                        "default_action": "idle",
                        "actions": {
                            "idle": {"files": ["a.gif", "b.gif"], "duration_ms": 100, "weight": 1, "lines": []},
                            "happy": {"files": ["c.gif"], "duration_ms": 100, "weight": 1, "lines": []},
                        },
                    }
                ),
                encoding="utf-8",
            )
            manager = AssetManager(root / "manifest.json")

            paths = {manager.random_file_path() for _ in range(80)}

            self.assertEqual(paths, {root / "a.gif", root / "b.gif", root / "c.gif"})

    def test_packaged_manifest_has_many_shouting_lines(self):
        manager = AssetManager(resource_path("assets", "manifest.json"))
        lines = [
            line
            for name in manager.action_names
            for line in manager.get_action(name).lines
            if "shouting" in line
        ]

        self.assertGreaterEqual(len(lines), 18)
        self.assertTrue(any("最喜欢" in line for line in lines))
        self.assertTrue(any("辛苦" in line for line in lines))

    def test_packaged_manifest_has_richer_playful_shouting_lines(self):
        manager = AssetManager(resource_path("assets", "manifest.json"))
        lines = [
            line
            for name in manager.action_names
            for line in manager.get_action(name).lines
            if "shouting" in line
        ]

        self.assertGreaterEqual(len(lines), 42)
        self.assertTrue(any("本噜噜大王" in line for line in lines))
        self.assertTrue(any("贴贴" in line for line in lines))
        self.assertTrue(any("偷偷" in line for line in lines))

    def test_packaged_manifest_references_current_gif_pool(self):
        manifest_path = resource_path("assets", "manifest.json")
        manager = AssetManager(manifest_path)
        gif_dir = resource_path("assets", "lulu_transparent_gifs")
        manifest_paths = {
            path
            for name in manager.action_names
            for path in manager.get_action(name).file_paths
        }

        self.assertTrue(manifest_paths)
        self.assertTrue(all(path.exists() for path in manifest_paths))
        self.assertTrue(any(path.name.startswith("640") for path in manifest_paths))
        self.assertTrue(set(gif_dir.glob("640*.gif")).issubset(manifest_paths))


if __name__ == "__main__":
    unittest.main()
