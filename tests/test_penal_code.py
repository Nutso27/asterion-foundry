"""Tests for the Directorate Penal Code.

Run from the repository root with:
    python -m unittest tests/test_penal_code.py -v
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from penal_code import (  # noqa: E402
    CAPITAL_TIER,
    PenalCode,
    SentencingTier,
    charge,
    confirm_capital_sentence,
)


class PenalCodeTests(unittest.TestCase):
    def setUp(self):
        self.code = PenalCode.default_code()

    def test_doctrine(self):
        self.assertEqual(self.code.doctrine, "Innocence Proves Nothing")

    def test_five_founding_articles(self):
        self.assertEqual(len(self.code.articles), 5)

    def test_charge_returns_typical_sentence(self):
        self.assertEqual(
            charge(self.code, "desertion_of_post"), SentencingTier.TOIL_LEGION
        )
        self.assertEqual(
            charge(self.code, "treason_against_the_directorate"), CAPITAL_TIER
        )

    def test_charge_unknown_article_raises(self):
        with self.assertRaises(KeyError):
            charge(self.code, "not_a_real_article")


class CapitalSentenceConfirmationTests(unittest.TestCase):
    def test_requires_both_signoffs(self):
        with self.assertRaises(ValueError):
            confirm_capital_sentence(referred_by_vigil=False, confirmed_by_grand_director=False)
        with self.assertRaises(ValueError):
            confirm_capital_sentence(referred_by_vigil=True, confirmed_by_grand_director=False)
        with self.assertRaises(ValueError):
            confirm_capital_sentence(referred_by_vigil=False, confirmed_by_grand_director=True)

    def test_fully_confirmed_succeeds(self):
        self.assertTrue(
            confirm_capital_sentence(referred_by_vigil=True, confirmed_by_grand_director=True)
        )


if __name__ == "__main__":
    unittest.main()
