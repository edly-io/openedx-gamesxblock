"""
Tests that studio_view renders correctly for every game type and round-trips
previously authored content back into the page (as the JSON blob studio.js reads).
"""

import json

from django.test import SimpleTestCase

from openedx_gamesxblock.constants import CardField, ClozeField, GameType, MemoryField, SequenceField

from .test_utils import make_block


class StudioViewTests(SimpleTestCase):
    """Verify studio_view renders for every game_type and includes previously authored content."""

    def test_renders_for_every_game_type(self):
        for game_type in GameType.ALL:
            with self.subTest(game_type=game_type):
                block = make_block(game_type=game_type)
                frag = block.studio_view()
                self.assertIn("gx-studio-game-type", frag.content)
                self.assertIn(f'value="{game_type}"', frag.content)

    def test_includes_row_templates_for_every_game(self):
        block = make_block()
        frag = block.studio_view()
        for template_id in (
            "gx-card-row-template", "gx-sequence-row-template", "gx-blank-row-template",
            "gx-word-row-template", "gx-memory-row-template",
        ):
            self.assertIn(template_id, frag.content)

    def test_previously_authored_matching_cards_round_trip_into_initial_data(self):
        cards = [{CardField.CARD_ID: "1", CardField.TERM: "A", CardField.TERM_IMAGE: "",
                  CardField.DEFINITION: "one", CardField.DEFINITION_IMAGE: ""}]
        block = make_block(game_type=GameType.MATCHING, cards=cards)
        frag = block.studio_view()

        blob = _extract_initial_data(frag.content)
        self.assertEqual(blob["cards"], cards)

    def test_previously_authored_sequence_items_round_trip(self):
        items = [{SequenceField.ITEM_ID: "a", SequenceField.TEXT: "Step one"}]
        block = make_block(game_type=GameType.SEQUENCING, sequence_items=items)
        frag = block.studio_view()
        blob = _extract_initial_data(frag.content)
        self.assertEqual(blob["sequence_items"], items)

    def test_wordsearch_words_normalized_to_dicts_in_initial_data(self):
        block = make_block(game_type=GameType.WORD_SEARCH, wordsearch_words=["CAT", "DOG"])
        frag = block.studio_view()
        blob = _extract_initial_data(frag.content)
        self.assertEqual(blob["wordsearch_words"], [{"word": "CAT"}, {"word": "DOG"}])

    def test_memory_pairs_round_trip(self):
        pairs = [{MemoryField.PAIR_ID: "p1", MemoryField.A: "Cat", MemoryField.B: "Meow"}]
        block = make_block(game_type=GameType.MEMORY, memory_pairs=pairs)
        frag = block.studio_view()
        blob = _extract_initial_data(frag.content)
        self.assertEqual(blob["memory_pairs"], pairs)

    def test_cloze_text_and_blanks_round_trip(self):
        blanks = [{ClozeField.TOKEN: "c1", ClozeField.ANSWERS: ["Paris"], ClozeField.DISTRACTORS: []}]
        block = make_block(game_type=GameType.CLOZE, cloze_text="City: {{c1}}", cloze_blanks=blanks)
        frag = block.studio_view()
        self.assertIn("City: {{c1}}", frag.content)
        blob = _extract_initial_data(frag.content)
        self.assertEqual(blob["cloze_blanks"], blanks)


def _extract_initial_data(html):
    """Pull out and parse the JSON blob embedded for studio.js to read."""
    marker = '<script type="application/json" id="gx-studio-initial-data">'
    start = html.index(marker) + len(marker)
    end = html.index("</script>", start)
    return json.loads(html[start:end])
