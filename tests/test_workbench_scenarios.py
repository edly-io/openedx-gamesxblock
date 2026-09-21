"""
Tests for OpenedxGamesXBlock's workbench_scenarios and top-level scoring contract.
"""

from django.test import SimpleTestCase

from openedx_gamesxblock.constants import GameType
from openedx_gamesxblock.games_block import OpenedxGamesXBlock

from .test_utils import make_block


class WorkbenchScenariosTests(SimpleTestCase):
    """Verify the canned scenarios are well-formed and cover every game type."""

    def test_returns_a_scenario_for_every_game_type(self):
        scenarios = OpenedxGamesXBlock.workbench_scenarios()
        combined_xml = " ".join(xml for _label, xml in scenarios)
        for game_type in GameType.ALL:
            with self.subTest(game_type=game_type):
                self.assertIn(f'game_type="{game_type}"', combined_xml)

    def test_scenario_labels_are_unique(self):
        scenarios = OpenedxGamesXBlock.workbench_scenarios()
        labels = [label for label, _xml in scenarios]
        self.assertEqual(len(labels), len(set(labels)))


class ScoreContractTests(SimpleTestCase):
    """Verify max_score/get_score follow the has_score XBlock contract for graded vs ungraded games."""

    def test_max_score_returns_weight_for_graded_games(self):
        block = make_block(game_type=GameType.MATCHING, weight=2.5)
        self.assertEqual(block.max_score(), 2.5)

    def test_max_score_is_none_for_ungraded_games(self):
        block = make_block(game_type=GameType.WORD_SEARCH)
        self.assertIsNone(block.max_score())

    def test_get_score_reports_best_earned_over_weight(self):
        block = make_block(game_type=GameType.MATCHING, weight=2.0, raw_earned=1.5)
        self.assertEqual(block.get_score(), {"score": 1.5, "total": 2.0})

    def test_get_score_is_none_for_ungraded_games(self):
        block = make_block(game_type=GameType.MEMORY)
        self.assertIsNone(block.get_score())

    def test_has_score_is_declared_true(self):
        # Required by the XBlock grading contract regardless of the current game_type,
        # since a single block instance can be reconfigured between graded and ungraded.
        self.assertTrue(OpenedxGamesXBlock.has_score)
