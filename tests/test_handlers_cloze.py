"""
Tests for the cloze game's student_view rendering and submit_cloze handler.
"""

import json

from django.test import SimpleTestCase

from openedx_gamesxblock.constants import ClozeField, GameType

from .test_utils import make_block

BLANKS = [{ClozeField.TOKEN: "c1", ClozeField.ANSWERS: ["Paris"], ClozeField.DISTRACTORS: ["London"]}]
PASSAGE = "The capital of France is {{c1}}."


class _FakeRequest:
    method = "POST"

    def __init__(self, payload):
        self.body = json.dumps(payload).encode("utf-8")


class ClozeStudentViewTests(SimpleTestCase):
    """Verify the passage renders with blanks and a word bank."""

    def test_renders_passage_segments_and_word_bank(self):
        block = make_block(game_type=GameType.CLOZE, cloze_text=PASSAGE, cloze_blanks=BLANKS)
        frag = block.student_view()
        self.assertIn("gx-cloze-blank", frag.content)
        self.assertIn("Paris", frag.content)  # in the word bank
        self.assertIn("London", frag.content)  # distractor also in the word bank

    def test_empty_blanks_renders_placeholder(self):
        block = make_block(game_type=GameType.CLOZE, cloze_text="", cloze_blanks=[])
        frag = block.student_view()
        self.assertIn("no blanks configured", frag.content)


class ClozeSubmitTests(SimpleTestCase):
    """Verify submit_cloze scores correctly and publishes a grade."""

    def test_correct_fill_scores_full_marks(self):
        block = make_block(game_type=GameType.CLOZE, cloze_text=PASSAGE, cloze_blanks=BLANKS)
        response = json.loads(block.submit_cloze(_FakeRequest({"fill": {"c1": "Paris"}})).body)
        self.assertEqual(response["raw_earned"], 1)
        self.assertEqual(block.runtime.published_events, [("grade", {"value": 1.0, "max_value": 1.0})])

    def test_wrong_fill_scores_zero_and_reveals_correct_answer(self):
        block = make_block(game_type=GameType.CLOZE, cloze_text=PASSAGE, cloze_blanks=BLANKS)
        response = json.loads(block.submit_cloze(_FakeRequest({"fill": {"c1": "London"}})).body)
        self.assertEqual(response["raw_earned"], 0)
        self.assertEqual(response["per_item"][0]["correct_answer"], "Paris")

    def test_max_attempts_enforced(self):
        block = make_block(game_type=GameType.CLOZE, cloze_text=PASSAGE, cloze_blanks=BLANKS, max_attempts=1)
        block.submit_cloze(_FakeRequest({"fill": {"c1": "Paris"}}))
        second = block.submit_cloze(_FakeRequest({"fill": {"c1": "Paris"}}))
        self.assertEqual(second.status_code, 403)
