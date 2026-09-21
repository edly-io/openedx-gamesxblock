"""
Tests for the matching game's student_view rendering and submit_matching handler.
"""

import json

from django.test import SimpleTestCase

from openedx_gamesxblock.constants import CardField, GameType
from openedx_gamesxblock.handlers import matching as matching_module

from .test_utils import make_block

CARDS = [
    {CardField.CARD_ID: "1", CardField.TERM: "A", CardField.TERM_IMAGE: "",
     CardField.DEFINITION: "one", CardField.DEFINITION_IMAGE: ""},
    {CardField.CARD_ID: "2", CardField.TERM: "B", CardField.TERM_IMAGE: "",
     CardField.DEFINITION: "two", CardField.DEFINITION_IMAGE: ""},
]


class _FakeRequest:
    """A minimal stand-in for the webob Request that XBlock.json_handler expects."""

    method = "POST"

    def __init__(self, payload):
        self.body = json.dumps(payload).encode("utf-8")


def _correct_pairs_for(block):
    """Recompute the HMAC tags for `block`'s current session so a fully-correct submission can be built."""
    session_key = bytes.fromhex(block.session_key_hex)
    return {
        card[CardField.CARD_ID]: matching_module._card_hmac(  # pylint: disable=protected-access
            session_key, card[CardField.CARD_ID]
        )
        for card in block.cards
    }


class MatchingStudentViewTests(SimpleTestCase):
    """Verify the matching board renders without exposing the answer key."""

    def test_renders_without_error(self):
        block = make_block(game_type=GameType.MATCHING, cards=CARDS)
        frag = block.student_view()
        self.assertIn("gx-matching-board", frag.content)
        self.assertIn("A", frag.content)
        self.assertIn("one", frag.content)

    def test_definition_side_never_exposes_real_card_id(self):
        block = make_block(game_type=GameType.MATCHING, cards=CARDS)
        frag = block.student_view()
        # The real card_id ("1", "2") must not appear as the definition's identifying attribute.
        self.assertNotIn('data-card-id="1"', frag.content.split("gx-matching-column-right")[1])

    def test_empty_cards_renders_placeholder_message(self):
        block = make_block(game_type=GameType.MATCHING, cards=[])
        frag = block.student_view()
        self.assertIn("no pairs configured", frag.content)

    def test_session_key_regenerates_each_render(self):
        block = make_block(game_type=GameType.MATCHING, cards=CARDS)
        block.student_view()
        first_key = block.session_key_hex
        block.student_view()
        self.assertNotEqual(first_key, block.session_key_hex)


class MatchingSubmitTests(SimpleTestCase):
    """Verify submit_matching scores correctly and publishes a grade."""

    def test_fully_correct_submission_scores_full_marks_and_publishes_grade(self):
        block = make_block(game_type=GameType.MATCHING, cards=CARDS)
        block.student_view()

        response = json.loads(block.submit_matching(_FakeRequest({"pairs": _correct_pairs_for(block)})).body)
        self.assertEqual(response["raw_earned"], 2)
        self.assertEqual(response["fraction"], 1.0)
        self.assertEqual(block.runtime.published_events, [("grade", {"value": 1.0, "max_value": 1.0})])

    def test_wrong_submission_scores_zero(self):
        block = make_block(game_type=GameType.MATCHING, cards=CARDS)
        block.student_view()
        swapped = _correct_pairs_for(block)
        keys = list(swapped.keys())
        swapped[keys[0]], swapped[keys[1]] = swapped[keys[1]], swapped[keys[0]]

        response = json.loads(block.submit_matching(_FakeRequest({"pairs": swapped})).body)
        self.assertEqual(response["raw_earned"], 0)

    def test_unconnected_terms_omitted_from_payload_score_as_wrong(self):
        block = make_block(game_type=GameType.MATCHING, cards=CARDS)
        block.student_view()
        response = json.loads(block.submit_matching(_FakeRequest({"pairs": {}})).body)
        self.assertEqual(response["raw_earned"], 0)
        self.assertEqual(response["raw_possible"], 2)

    def test_stale_tag_from_a_previous_render_does_not_score_correct(self):
        """A tag captured before a re-render must not validate against the new session key."""
        block = make_block(game_type=GameType.MATCHING, cards=CARDS)
        block.student_view()
        stale_pairs = _correct_pairs_for(block)
        block.student_view()  # regenerates session_key_hex

        response = json.loads(block.submit_matching(_FakeRequest({"pairs": stale_pairs})).body)
        self.assertEqual(response["raw_earned"], 0)

    def test_attempts_increment_and_are_enforced(self):
        block = make_block(game_type=GameType.MATCHING, cards=CARDS, max_attempts=1)
        block.student_view()
        pairs = _correct_pairs_for(block)

        first = block.submit_matching(_FakeRequest({"pairs": pairs}))
        self.assertEqual(first.status_code, 200)
        self.assertEqual(block.attempts, 1)

        second = block.submit_matching(_FakeRequest({"pairs": pairs}))
        self.assertEqual(second.status_code, 403)

    def test_retry_keeps_best_score_never_lowers_it(self):
        block = make_block(game_type=GameType.MATCHING, cards=CARDS, max_attempts=0)
        block.student_view()
        correct_pairs = _correct_pairs_for(block)
        block.submit_matching(_FakeRequest({"pairs": correct_pairs}))
        self.assertEqual(block.raw_earned, 1.0)

        block.student_view()  # new render/session for the retry
        response = json.loads(block.submit_matching(_FakeRequest({"pairs": {}})).body)
        self.assertEqual(response["raw_earned"], 0)
        self.assertFalse(response["is_new_best"])
        self.assertEqual(block.raw_earned, 1.0)  # unchanged -- best attempt is kept
