import unittest
from pathlib import Path

from pipeline import EDIT_STYLES


ROOT = Path(__file__).resolve().parents[1]


class AppleEditingUITests(unittest.TestCase):
    def test_motion_skill_panel_is_removed(self):
        html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
        self.assertNotIn("动效 Skill", html)
        self.assertNotIn('id="motionGrid"', html)

    def test_advanced_jianying_and_kaipai_templates_exist(self):
        expected = {
            "jianying_big",
            "jianying_clean",
            "keyword_punch",
            "kaipai_talk",
            "kaipai_boss",
            "kaipai_story",
        }
        self.assertTrue(expected.issubset(EDIT_STYLES))

    def test_motion_is_derived_from_editing_template(self):
        script = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
        self.assertIn("MOTION_BY_STYLE", script)
        self.assertNotIn('input[name="motion"]', script)


if __name__ == "__main__":
    unittest.main()
