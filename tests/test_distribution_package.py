"""Verify the public Claude skill carries the intended licensing terms."""

from __future__ import annotations

import re
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "digital-album"
ARCHIVE = ROOT / "dist" / "digital-album.zip"


class DistributionPackageTests(unittest.TestCase):
    """Protect the licensing and Claude package layout from regressions."""

    def test_current_release_uses_polyform_noncommercial(self) -> None:
        root_license = (ROOT / "LICENSE").read_text(encoding="utf-8")
        skill_license = (SKILL / "LICENSE").read_text(encoding="utf-8")

        self.assertEqual(root_license, skill_license)
        self.assertTrue(
            root_license.startswith("# PolyForm Noncommercial License 1.0.0")
        )
        self.assertIn(
            "Required Notice: Copyright 2026 Idan Shenhav.", root_license
        )
        self.assertNotIn("Permission is hereby granted, free of charge", root_license)

    def test_version_and_commercial_notice_are_packaged(self) -> None:
        self.assertEqual(
            "2.0.0", (SKILL / "VERSION").read_text(encoding="utf-8").strip()
        )
        self.assertEqual(
            (ROOT / "COMMERCIAL-LICENSE.md").read_text(encoding="utf-8"),
            (SKILL / "COMMERCIAL-LICENSE.md").read_text(encoding="utf-8"),
        )

        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("PolyForm Noncommercial License 1.0.0", readme)
        self.assertIn("Personal use is free", readme)
        self.assertIn("Commercial use requires a separate written license", readme)
        self.assertIn("print house, album maker, photo-book company", readme)

    def test_claude_skill_frontmatter_and_layout_remain_valid(self) -> None:
        skill_text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        frontmatter = re.match(r"\A---\n(.*?)\n---\n", skill_text, re.DOTALL)

        self.assertIsNotNone(frontmatter)
        self.assertIn("name: digital-album", frontmatter.group(1))
        self.assertIn("description:", frontmatter.group(1))
        self.assertIn("## License", skill_text)
        self.assertTrue((SKILL / "references" / "cowork-setup.md").is_file())
        self.assertTrue((SKILL / "scripts" / "build_plan.py").is_file())

    def test_release_zip_is_a_claude_installable_skill(self) -> None:
        self.assertTrue(ARCHIVE.is_file(), f"Missing release archive: {ARCHIVE}")

        with zipfile.ZipFile(ARCHIVE) as archive:
            names = set(archive.namelist())
            files = {name for name in names if not name.endswith("/")}

            self.assertIn("digital-album/SKILL.md", files)
            self.assertIn("digital-album/LICENSE", files)
            self.assertIn("digital-album/COMMERCIAL-LICENSE.md", files)
            self.assertIn("digital-album/VERSION", files)
            self.assertTrue(all(name.startswith("digital-album/") for name in files))


if __name__ == "__main__":
    unittest.main()
