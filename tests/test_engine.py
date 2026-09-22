"""The detector has to earn trust on files whose answer we already know.

Every fixture is synthesised with a cutoff we chose, so these are not
regression snapshots - they assert the tool finds the wall that is actually
there, and does not invent one where there is none.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import fixtures  # noqa: E402
from losslessaudit import engine, i18n  # noqa: E402


class TestCleanFile(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = engine.analyse(fixtures.full_band())

    def test_no_wall_is_reported(self):
        self.assertFalse(self.r["has_wall"],
                         "found a wall in a file that has none")

    def test_scores_top_marks(self):
        self.assertGreaterEqual(self.r["total"], 95)
        self.assertEqual(self.r["grade"], "grade.excellent")

    def test_not_flagged_as_lossy(self):
        self.assertFalse(self.r["proven_lossy"])


class TestWallDetection(unittest.TestCase):
    def test_finds_wall_at_16k(self):
        r = engine.analyse(fixtures.wall_at_16k())
        self.assertTrue(r["has_wall"])
        self.assertAlmostEqual(r["wall_hz"], 16000, delta=400)
        self.assertTrue(r["proven_lossy"])

    def test_finds_wall_at_20k(self):
        r = engine.analyse(fixtures.wall_at_20k())
        self.assertTrue(r["has_wall"])
        self.assertAlmostEqual(r["wall_hz"], 20000, delta=400)
        self.assertTrue(r["proven_lossy"])

    def test_lower_wall_scores_worse(self):
        low = engine.analyse(fixtures.wall_at_16k())["total"]
        high = engine.analyse(fixtures.wall_at_20k())["total"]
        clean = engine.analyse(fixtures.full_band())["total"]
        self.assertLess(low, high)
        self.assertLess(high, clean)

    def test_proven_lossy_cannot_score_well(self):
        # Without the cap a fake FLAC reaches ~87 on its other merits.
        r = engine.analyse(fixtures.wall_at_20k())
        self.assertLess(r["total"], 60)
        self.assertEqual(r["tag"], "tag.from_lossy")


class TestClipping(unittest.TestCase):
    def test_clipping_costs_headroom(self):
        r = engine.analyse(fixtures.clipped())
        self.assertGreater(r["clip_ratio"], 0.0)
        headroom = [p for p in r["parts"] if p["key"] == "part.headroom"][0]
        self.assertLess(headroom["got"], headroom["max"])


class TestErrors(unittest.TestCase):
    def test_missing_file(self):
        r = engine.analyse("/nonexistent/nope.flac")
        self.assertIn("error", r)

    def test_not_audio(self):
        r = engine.analyse(__file__)
        self.assertIn("error", r)


class TestTranslations(unittest.TestCase):
    def test_every_language_covers_every_key(self):
        keys = set(i18n.MESSAGES["en"])
        for lang in i18n.LANGUAGES:
            self.assertEqual(set(i18n.MESSAGES[lang]), keys,
                             "language %r is out of sync" % lang)

    def test_every_code_the_engine_emits_exists(self):
        r = engine.analyse(fixtures.wall_at_16k())
        codes = [r["grade"], r["tag"]]
        for p in r["parts"]:
            codes.append(p["key"])
            codes.append(p["note"]["code"])
            if "suffix" in p["note"]:
                codes.append(p["note"]["suffix"]["code"])
        for lang in i18n.LANGUAGES:
            for c in codes:
                self.assertIn(c, i18n.MESSAGES[lang])

    def test_localise_fills_slots(self):
        r = engine.localise(engine.analyse(fixtures.wall_at_16k()), "en")
        note = [p["note_text"] for p in r["parts"] if p["key"] == "part.bandwidth"][0]
        self.assertIn("kHz", note)
        self.assertNotIn("{", note)

    def test_score_is_language_independent(self):
        r = engine.analyse(fixtures.wall_at_16k())
        self.assertEqual(engine.localise(r, "en")["total"],
                         engine.localise(r, "fa")["total"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
