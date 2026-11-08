"""Run with: python3 -m unittest discover tests"""
import json, re, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class ActivityTest(unittest.TestCase):
    def test_fixture_renders_and_updates_readme(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            shutil.copytree(ROOT / "scripts", work / "scripts")
            shutil.copy(ROOT / "README.md", work / "README.md")
            out = subprocess.run([sys.executable, "scripts/activity.py", "--fixture", str(ROOT / "tests/calendar.json")], cwd=work, capture_output=True, text=True)
            self.assertEqual(out.returncode, 0, out.stderr)
            svg = (work / "assets/activity.svg").read_text()
            fixture = json.loads((ROOT / "tests/calendar.json").read_text())
            days = sum(len(w["contributionDays"]) for w in fixture["weeks"])
            self.assertEqual(svg.count("<rect x="), days)
            self.assertIn(f'{fixture["totalContributions"]} contributions', svg)
            readme = (work / "README.md").read_text()
            self.assertRegex(readme, rf'\*\*{fixture["totalContributions"]:,} contributions in the last year\.\*\*')
            # Idempotent: a second run leaves exactly one block.
            subprocess.run([sys.executable, "scripts/activity.py", "--fixture", str(ROOT / "tests/calendar.json")], cwd=work, check=True, capture_output=True)
            self.assertEqual((work / "README.md").read_text().count("activity:start"), 1)


if __name__ == "__main__":
    unittest.main()
