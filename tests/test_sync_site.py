"""Run with: python3 -m unittest discover tests"""
import json, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run(work: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "scripts/sync_site.py", *args], cwd=work, capture_output=True, text=True)


class SyncSiteTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.work = Path(self.tmp.name)
        shutil.copytree(ROOT / "scripts", self.work / "scripts")
        shutil.copy(ROOT / "README.md", self.work / "README.md")
        (self.work / "assets").mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def test_fixture_rewrites_table_and_banner(self):
        out = run(self.work, "--fixture", str(ROOT / "tests/site"))
        self.assertEqual(out.returncode, 0, out.stderr)
        feed = json.loads((ROOT / "tests/site/profile.json").read_text())
        readme = (self.work / "README.md").read_text()
        for w in feed["work"]:
            self.assertIn(f'**[{w["title"]}]({w["href"]})**', readme)
        self.assertIn("[code](https://github.com/shaincarrasco/D1-Basketball-Analytics)", readme)
        self.assertIn(f'alt="{feed["name"]}. {feed["tagline"]}"', readme)
        self.assertEqual((self.work / "assets/banner.svg").read_bytes(), (ROOT / "tests/site/banner.svg").read_bytes())
        # Hand-written parts survive.
        self.assertIn("### Summer 2026 at the SkAI Institute", readme)
        self.assertIn("<!-- activity:start -->", readme)
        # Idempotent.
        run(self.work, "--fixture", str(ROOT / "tests/site"))
        self.assertEqual((self.work / "README.md").read_text(), readme)

    def test_missing_feed_leaves_profile_untouched(self):
        before = (self.work / "README.md").read_text()
        out = run(self.work, "--fixture", str(self.work / "nowhere"))
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("Skipped", out.stdout)
        self.assertEqual((self.work / "README.md").read_text(), before)

    def test_pipes_in_text_are_escaped(self):
        sys.path.insert(0, str(ROOT / "scripts"))
        import sync_site
        table = sync_site.render_work({"work": [{"title": "A|B", "href": "https://x.y", "line": "one | two."}]})
        self.assertIn("A\\|B", table)
        self.assertIn("one \\| two.", table)


if __name__ == "__main__":
    unittest.main()
