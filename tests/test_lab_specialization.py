"""Tests for lab specialization (fixed roles vs. Lab #1's flexible pool).

Run from the repository root with:
    python -m unittest tests/test_lab_specialization.py -v
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from research.lab_specialization import (  # noqa: E402
    FLEXIBLE_AUTO_RESEARCH,
    PERPETUAL_CONSTRUCTION_OPTIMIZATION,
    PERPETUAL_RESEARCH_METHODOLOGY,
    PERPETUAL_UNIVERSAL_IMPROVEMENT,
    apply_perpetual_tick,
    default_lab_role,
)


class DefaultLabRoleTests(unittest.TestCase):
    def test_lab_one_is_flexible(self):
        self.assertEqual(default_lab_role(1), FLEXIBLE_AUTO_RESEARCH)

    def test_lab_two_and_three_have_dedicated_programs(self):
        self.assertEqual(default_lab_role(2), PERPETUAL_CONSTRUCTION_OPTIMIZATION)
        self.assertEqual(default_lab_role(3), PERPETUAL_RESEARCH_METHODOLOGY)

    def test_lab_four_and_beyond_default_to_universal_improvement(self):
        for lab_number in (4, 5, 6, 7, 20):
            self.assertEqual(default_lab_role(lab_number), PERPETUAL_UNIVERSAL_IMPROVEMENT)

    def test_rejects_lab_zero_or_negative(self):
        with self.assertRaises(ValueError):
            default_lab_role(0)


class ApplyPerpetualTickTests(unittest.TestCase):
    def test_moves_toward_floor(self):
        result = apply_perpetual_tick(multiplier=1.0, magnitude_per_tick=0.01, floor=0.5)
        self.assertAlmostEqual(result, 0.99)

    def test_never_crosses_floor(self):
        result = apply_perpetual_tick(multiplier=0.505, magnitude_per_tick=0.01, floor=0.5)
        self.assertEqual(result, 0.5)

    def test_rejects_negative_magnitude(self):
        with self.assertRaises(ValueError):
            apply_perpetual_tick(multiplier=1.0, magnitude_per_tick=-0.1, floor=0.5)


if __name__ == "__main__":
    unittest.main()
