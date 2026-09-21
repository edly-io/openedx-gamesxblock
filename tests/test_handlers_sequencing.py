"""
Tests for the sequencing game's student_view rendering and submit_sequencing handler.
"""

import json

from django.test import SimpleTestCase

from openedx_gamesxblock.constants import GameType, SequenceField

from .test_utils import make_block

ITEMS = [
    {SequenceField.ITEM_ID: "a", SequenceField.TEXT: "First"},
    {SequenceField.ITEM_ID: "b", SequenceField.TEXT: "Second"},
    {SequenceField.ITEM_ID: "c", SequenceField.TEXT: "Third"},
]


class _FakeRequest:
    method = "POST"

    def __init__(self, payload):
        self.body = json.dumps(payload).encode("utf-8")


class SequencingStudentViewTests(SimpleTestCase):
    """Verify the sequencing board renders shuffled items without exposing the correct order."""

    def test_renders_without_error(self):
        block = make_block(game_type=GameType.SEQUENCING, sequence_items=ITEMS)
        frag = block.student_view()
        self.assertIn("gx-sequencing-list", frag.content)
        self.assertIn("First", frag.content)

    def test_empty_items_renders_placeholder(self):
        block = make_block(game_type=GameType.SEQUENCING, sequence_items=[])
        frag = block.student_view()
        self.assertIn("no steps configured", frag.content)


class SequencingSubmitTests(SimpleTestCase):
    """Verify submit_sequencing scores correctly and publishes a grade."""

    def test_correct_order_scores_full_marks(self):
        block = make_block(game_type=GameType.SEQUENCING, sequence_items=ITEMS)
        response = json.loads(block.submit_sequencing(_FakeRequest({"order": ["a", "b", "c"]})).body)
        self.assertEqual(response["raw_earned"], 3)
        self.assertEqual(response["fraction"], 1.0)
        self.assertEqual(block.runtime.published_events, [("grade", {"value": 1.0, "max_value": 1.0})])

    def test_partial_order_gives_partial_credit(self):
        block = make_block(game_type=GameType.SEQUENCING, sequence_items=ITEMS)
        response = json.loads(block.submit_sequencing(_FakeRequest({"order": ["b", "a", "c"]})).body)
        self.assertEqual(response["raw_earned"], 1)  # only "c" is in its exact correct slot

    def test_missing_order_key_scores_zero_without_crashing(self):
        block = make_block(game_type=GameType.SEQUENCING, sequence_items=ITEMS)
        response = json.loads(block.submit_sequencing(_FakeRequest({})).body)
        self.assertEqual(response["raw_earned"], 0)

    def test_max_attempts_enforced(self):
        block = make_block(game_type=GameType.SEQUENCING, sequence_items=ITEMS, max_attempts=1)
        block.submit_sequencing(_FakeRequest({"order": ["a", "b", "c"]}))
        second = block.submit_sequencing(_FakeRequest({"order": ["a", "b", "c"]}))
        self.assertEqual(second.status_code, 403)
