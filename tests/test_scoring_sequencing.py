"""
Tests for openedx_gamesxblock.scoring.sequencing -- pure functions, no XBlock runtime needed.

Scoring uses a longest-increasing-subsequence approach so a single displaced
item doesn't zero out the whole submission; see the docstring in
scoring/sequencing.py for the full rationale.
"""

from django.test import SimpleTestCase

from openedx_gamesxblock.scoring.sequencing import score_sequencing

CORRECT_ORDER = ["a", "b", "c", "d"]


class ScoreSequencingTests(SimpleTestCase):
    """Verify LCS-based partial-credit sequencing scoring."""

    def test_perfect_order(self):
        result = score_sequencing(CORRECT_ORDER, ["a", "b", "c", "d"])
        self.assertEqual(result.raw_earned, 4)
        self.assertEqual(result.fraction, 1.0)
        self.assertTrue(all(item["correct"] for item in result.per_item))

    def test_fully_reversed_scores_zero(self):
        result = score_sequencing(CORRECT_ORDER, ["d", "c", "b", "a"])
        self.assertEqual(result.raw_earned, 0)

    def test_one_swap_gives_partial_credit_not_zero(self):
        # b and c swapped: a and d are still in their exact correct slots.
        result = score_sequencing(CORRECT_ORDER, ["a", "c", "b", "d"])
        self.assertEqual(result.raw_earned, 2)
        per_item_by_id = {item["id"]: item for item in result.per_item}
        self.assertTrue(per_item_by_id["a"]["correct"])
        self.assertTrue(per_item_by_id["d"]["correct"])
        self.assertFalse(per_item_by_id["b"]["correct"])
        self.assertFalse(per_item_by_id["c"]["correct"])

    def test_leading_shift_does_not_zero_the_tail(self):
        # b moved to the front, shifting a/b but leaving c/d in their absolute slots.
        result = score_sequencing(CORRECT_ORDER, ["b", "a", "c", "d"])
        self.assertEqual(result.raw_earned, 2)
        per_item_by_id = {item["id"]: item for item in result.per_item}
        self.assertTrue(per_item_by_id["c"]["correct"])
        self.assertTrue(per_item_by_id["d"]["correct"])

    def test_correct_position_reported_for_reveal(self):
        result = score_sequencing(CORRECT_ORDER, ["b", "a", "c", "d"])
        per_item_by_id = {item["id"]: item for item in result.per_item}
        self.assertEqual(per_item_by_id["a"]["correct_position"], 0)
        self.assertEqual(per_item_by_id["b"]["correct_position"], 1)

    def test_unknown_item_id_never_contributes_to_score(self):
        result = score_sequencing(CORRECT_ORDER, ["a", "b", "unknown", "c", "d"])
        self.assertEqual(result.raw_possible, 4)
        per_item_by_id = {item["id"]: item for item in result.per_item}
        self.assertFalse(per_item_by_id["unknown"]["correct"])
        self.assertIsNone(per_item_by_id["unknown"]["correct_position"])

    def test_empty_order_no_divide_by_zero(self):
        result = score_sequencing([], [])
        self.assertEqual(result.raw_possible, 0)
        self.assertEqual(result.fraction, 0.0)
