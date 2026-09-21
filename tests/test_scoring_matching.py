"""
Tests for openedx_gamesxblock.scoring.matching -- pure functions, no XBlock runtime needed.
"""

from django.test import SimpleTestCase

from openedx_gamesxblock.scoring.matching import score_matching

CARDS = [
    {"card_id": "1", "term": "Photosynthesis", "definition": "How plants make food from light"},
    {"card_id": "2", "term": "Mitosis", "definition": "Cell division producing identical cells"},
    {"card_id": "3", "term": "Osmosis", "definition": "Movement of water across a membrane"},
]


class ScoreMatchingTests(SimpleTestCase):
    """Verify partial-credit matching scoring."""

    def test_all_correct(self):
        submitted = {"1": "1", "2": "2", "3": "3"}
        result = score_matching(CARDS, submitted)
        self.assertEqual(result.raw_earned, 3)
        self.assertEqual(result.raw_possible, 3)
        self.assertEqual(result.fraction, 1.0)
        self.assertTrue(all(item["correct"] for item in result.per_item))

    def test_all_wrong(self):
        submitted = {"1": "2", "2": "3", "3": "1"}
        result = score_matching(CARDS, submitted)
        self.assertEqual(result.raw_earned, 0)
        self.assertEqual(result.fraction, 0.0)

    def test_partial_credit(self):
        submitted = {"1": "1", "2": "3", "3": "1"}  # only card 1 correct
        result = score_matching(CARDS, submitted)
        self.assertEqual(result.raw_earned, 1)
        self.assertEqual(result.raw_possible, 3)
        self.assertAlmostEqual(result.fraction, 1 / 3)

    def test_unconnected_term_counts_as_wrong(self):
        submitted = {"1": "1"}  # cards 2 and 3 never connected
        result = score_matching(CARDS, submitted)
        self.assertEqual(result.raw_earned, 1)
        per_item_by_id = {item["id"]: item for item in result.per_item}
        self.assertFalse(per_item_by_id["2"]["correct"])
        self.assertIsNone(per_item_by_id["2"]["submitted_answer"])

    def test_per_item_reveals_correct_answer_on_miss(self):
        submitted = {"1": "2", "2": "1", "3": "3"}
        result = score_matching(CARDS, submitted)
        per_item_by_id = {item["id"]: item for item in result.per_item}
        self.assertEqual(per_item_by_id["1"]["correct_answer"], "How plants make food from light")
        self.assertEqual(per_item_by_id["1"]["submitted_answer"], "Cell division producing identical cells")

    def test_empty_cards_gives_zero_possible_and_no_divide_by_zero(self):
        result = score_matching([], {})
        self.assertEqual(result.raw_possible, 0)
        self.assertEqual(result.fraction, 0.0)

    def test_invalid_submitted_id_treated_as_wrong(self):
        submitted = {"1": "does-not-exist", "2": "2", "3": "3"}
        result = score_matching(CARDS, submitted)
        self.assertEqual(result.raw_earned, 2)
        per_item_by_id = {item["id"]: item for item in result.per_item}
        self.assertIsNone(per_item_by_id["1"]["submitted_answer"])
