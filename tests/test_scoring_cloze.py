"""
Tests for openedx_gamesxblock.scoring.cloze -- pure functions, no XBlock runtime needed.
"""

from django.test import SimpleTestCase

from openedx_gamesxblock.scoring.cloze import score_cloze

BLANKS = [
    {"token": "blank1", "answers": ["Paris"]},
    {"token": "blank2", "answers": ["mitochondria", "mitochondrion"]},
]


class ScoreClozeTests(SimpleTestCase):
    """Verify per-blank, case-insensitive cloze scoring."""

    def test_all_correct(self):
        result = score_cloze(BLANKS, {"blank1": "Paris", "blank2": "mitochondria"})
        self.assertEqual(result.raw_earned, 2)
        self.assertEqual(result.fraction, 1.0)

    def test_case_insensitive_match(self):
        result = score_cloze(BLANKS, {"blank1": "paris", "blank2": "MITOCHONDRIA"})
        self.assertEqual(result.raw_earned, 2)

    def test_whitespace_insensitive_match(self):
        result = score_cloze(BLANKS, {"blank1": "  Paris  ", "blank2": "mitochondria"})
        self.assertEqual(result.raw_earned, 2)

    def test_synonym_accepted(self):
        result = score_cloze(BLANKS, {"blank1": "Paris", "blank2": "mitochondrion"})
        self.assertEqual(result.raw_earned, 2)

    def test_partial_credit_for_one_wrong_blank(self):
        result = score_cloze(BLANKS, {"blank1": "London", "blank2": "mitochondria"})
        self.assertEqual(result.raw_earned, 1)
        per_item_by_id = {item["id"]: item for item in result.per_item}
        self.assertFalse(per_item_by_id["blank1"]["correct"])
        self.assertEqual(per_item_by_id["blank1"]["correct_answer"], "Paris")

    def test_empty_submission_scores_zero(self):
        result = score_cloze(BLANKS, {})
        self.assertEqual(result.raw_earned, 0)
        self.assertEqual(result.raw_possible, 2)

    def test_missing_answers_list_never_crashes(self):
        blanks = [{"token": "blank1", "answers": []}]
        result = score_cloze(blanks, {"blank1": "anything"})
        self.assertEqual(result.raw_earned, 0)
        self.assertIsNone(result.per_item[0]["correct_answer"])
