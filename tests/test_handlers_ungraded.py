"""
Tests for the ungraded games (word search, memory): student_view rendering
and completion handlers must never publish a grade event.
"""

import json

from django.test import SimpleTestCase

from openedx_gamesxblock.constants import GameType, MemoryField

from .test_utils import make_block


class _FakeRequest:
    method = "POST"

    def __init__(self, payload):
        self.body = json.dumps(payload).encode("utf-8")


class WordSearchTests(SimpleTestCase):
    """Verify the word search game renders a grid and tracks completion without grading."""

    def test_renders_grid_containing_every_word(self):
        block = make_block(game_type=GameType.WORD_SEARCH, wordsearch_words=["CAT", "DOG"])
        frag = block.student_view()
        self.assertIn("gx-wordsearch-grid", frag.content)
        self.assertIn("CAT", frag.content)
        self.assertIn("DOG", frag.content)

    def test_empty_words_renders_placeholder(self):
        block = make_block(game_type=GameType.WORD_SEARCH, wordsearch_words=[])
        frag = block.student_view()
        self.assertIn("no words configured", frag.content)

    def test_completion_records_best_time_without_publishing_grade(self):
        block = make_block(game_type=GameType.WORD_SEARCH, wordsearch_words=["CAT"])
        response = json.loads(block.complete_wordsearch(_FakeRequest({"time_seconds": 30})).body)
        self.assertEqual(response["best_time_seconds"], 30)
        self.assertTrue(response["is_new_best"])
        self.assertEqual(block.runtime.published_events, [])

    def test_best_time_only_improves_never_regresses(self):
        block = make_block(game_type=GameType.WORD_SEARCH, wordsearch_words=["CAT"], best_time_seconds=10)
        response = json.loads(block.complete_wordsearch(_FakeRequest({"time_seconds": 30})).body)
        self.assertEqual(block.best_time_seconds, 10)
        self.assertFalse(response["is_new_best"])

    def test_word_too_long_for_grid_is_skipped_without_crashing(self):
        # A word longer than the max grid size can never be placed; it's simply
        # omitted rather than crashing or growing the grid unboundedly. A normal
        # word alongside it should still be placed and rendered.
        block = make_block(game_type=GameType.WORD_SEARCH, wordsearch_words=["A" * 500, "CAT"])
        frag = block.student_view()  # must not raise
        self.assertIn("gx-wordsearch-grid", frag.content)
        self.assertIn("CAT", frag.content)


class MemoryTests(SimpleTestCase):
    """Verify the memory game renders face-down cards and tracks completion without grading."""

    def test_renders_two_cards_per_pair(self):
        pairs = [{MemoryField.PAIR_ID: "p1", MemoryField.A: "Cat", MemoryField.B: "Meow"}]
        block = make_block(game_type=GameType.MEMORY, memory_pairs=pairs)
        frag = block.student_view()
        self.assertEqual(frag.content.count('class="gx-memory-card"'), 2)

    def test_card_tags_are_not_the_plaintext_content(self):
        pairs = [{MemoryField.PAIR_ID: "p1", MemoryField.A: "Cat", MemoryField.B: "Meow"}]
        block = make_block(game_type=GameType.MEMORY, memory_pairs=pairs)
        frag = block.student_view()
        self.assertNotIn('data-tag="Cat"', frag.content)
        self.assertNotIn('data-tag="Meow"', frag.content)

    def test_completion_records_best_time_without_publishing_grade(self):
        block = make_block(game_type=GameType.MEMORY, memory_pairs=[])
        response = json.loads(block.complete_memory(_FakeRequest({"time_seconds": 20})).body)
        self.assertEqual(response["best_time_seconds"], 20)
        self.assertEqual(block.runtime.published_events, [])

    def test_empty_pairs_renders_placeholder(self):
        block = make_block(game_type=GameType.MEMORY, memory_pairs=[])
        frag = block.student_view()
        self.assertIn("no pairs configured", frag.content)
