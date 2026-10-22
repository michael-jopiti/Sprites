"""Run with: uv run python -m unittest"""
import unittest

from sprites import model
from sprites.library import valid

R, B = "#ff0000", "#0000ff"


class ResampleTest(unittest.TestCase):
    def setUp(self):
        self.g = model.blank(4)
        self.g[1][2] = R
        self.g[0][0] = self.g[0][1] = self.g[1][0] = B

    def test_grow_keeps_picture(self):
        up = model.resample(self.g, 8)
        self.assertEqual((up[2][4], up[3][5], up[0][0]), (R, R, B))
        self.assertEqual(model.resample(up, 4), self.g)

    def test_shrink_majority(self):
        self.assertEqual(model.resample(self.g, 2), [[B, None], [None, None]])

    def test_round_trip(self):
        self.assertEqual(model.resample(model.resample(model.resample(self.g, 16), 8), 4), self.g)


class NameTest(unittest.TestCase):
    def test_valid(self):
        self.assertTrue(valid("hero"))
        for bad in ("", "a/b", "a\\b", "a:b", ".hidden"):
            self.assertFalse(valid(bad))


if __name__ == "__main__":
    unittest.main()
