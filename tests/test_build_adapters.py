"""Unit tests for the adapter generator.

Run: python3 -m unittest tests.test_build_adapters
or:  python3 tests/test_build_adapters.py
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from tempfile import NamedTemporaryFile

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import importlib.util
spec = importlib.util.spec_from_file_location("build_adapters", ROOT / "scripts" / "build-adapters.py")
ba = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ba)  # type: ignore[union-attr]


class ParseFrontmatterTests(unittest.TestCase):
    def _tmp(self, text: str) -> Path:
        f = NamedTemporaryFile("w", suffix=".md", delete=False)
        f.write(text)
        f.close()
        return Path(f.name)

    def test_parses_simple_frontmatter(self) -> None:
        p = self._tmp("---\nname: foo\ndescription: bar\n---\nbody\n")
        fm, body = ba.parse(p)
        self.assertEqual(fm["name"], "foo")
        self.assertEqual(fm["description"], "bar")
        self.assertEqual(body.strip(), "body")

    def test_no_frontmatter_returns_empty_dict(self) -> None:
        p = self._tmp("no fm here\n")
        fm, body = ba.parse(p)
        self.assertEqual(fm, {})
        self.assertIn("no fm here", body)

    def test_strips_surrounding_quotes(self) -> None:
        p = self._tmp('---\nname: "quoted"\n---\nx\n')
        fm, _ = ba.parse(p)
        self.assertEqual(fm["name"], "quoted")


class LoadAllTests(unittest.TestCase):
    def test_load_all_finds_known_skills(self) -> None:
        items = ba.load_all()
        skill_names = {fm.get("name") for fm, _, _ in items["skills"]}
        self.assertIn("moodle-plugin-development", skill_names)
        self.assertIn("moodle-phpunit-testing", skill_names)

    def test_load_all_finds_known_commands(self) -> None:
        items = ba.load_all()
        cmd_names = {fm.get("name") for fm, _, _ in items["commands"]}
        self.assertIn("moodle-new-plugin", cmd_names)

    def test_load_all_finds_known_agents(self) -> None:
        items = ba.load_all()
        agent_names = {fm.get("name") for fm, _, _ in items["agents"]}
        self.assertIn("moodle-reviewer", agent_names)


class CodexPluginTests(unittest.TestCase):
    def test_manifest_exposes_existing_components(self) -> None:
        manifest = json.loads((ROOT / ".codex-plugin" / "plugin.json").read_text())

        self.assertEqual(manifest["name"], "moodle-dev")
        self.assertEqual(manifest["skills"], "./skills/")
        self.assertEqual(manifest["mcpServers"], "./.mcp.json")
        self.assertTrue((ROOT / "skills").is_dir())
        self.assertTrue((ROOT / "commands").is_dir())
        self.assertTrue((ROOT / "agents").is_dir())

        interface = manifest["interface"]
        self.assertEqual(interface["displayName"], "Moodle Dev")
        self.assertLessEqual(len(interface["defaultPrompt"]), 3)
        self.assertTrue(all(len(prompt) <= 128 for prompt in interface["defaultPrompt"]))

    def test_marketplace_installs_repository_plugin(self) -> None:
        marketplace = json.loads(
            (ROOT / ".agents" / "plugins" / "marketplace.json").read_text()
        )
        entry = marketplace["plugins"][0]

        self.assertEqual(marketplace["name"], "moodle-dev")
        self.assertEqual(entry["name"], "moodle-dev")
        self.assertEqual(entry["source"]["source"], "url")
        self.assertTrue(entry["source"]["url"].endswith("/claude-moodle-dev.git"))
        self.assertEqual(entry["policy"]["installation"], "AVAILABLE")
        self.assertEqual(entry["policy"]["authentication"], "ON_INSTALL")
        self.assertTrue(entry["category"])

    def test_mcp_companion_uses_uvx(self) -> None:
        mcp = json.loads((ROOT / ".mcp.json").read_text())
        server = mcp["mcpServers"]["moodle-mcp"]

        self.assertEqual(server["command"], "uvx")
        self.assertIn("moodle-mcp", server["args"])


if __name__ == "__main__":
    unittest.main()
