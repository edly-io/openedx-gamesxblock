"""
The Games XBlock: a single block that renders one of several mini-games
(matching, sequencing, cloze, word search, memory) selected by ``game_type``.

Authoring happens entirely through this block's own ``studio_view`` -- the
default XBlock editor experience already provided by the authoring MFE.
No changes to any MFE are required to author or grade content with this block.
"""

from django.utils.translation import gettext_lazy as _
from xblock.core import XBlock
from xblock.fields import Boolean, Dict, Float, Integer, List, Scope, String
from xblock.utils.resources import ResourceLoader

from .constants import Default, GameType
from .handlers.cloze import ClozeHandlers
from .handlers.common import CommonHandlers
from .handlers.matching import MatchingHandlers
from .handlers.memory import MemoryHandlers
from .handlers.sequencing import SequencingHandlers
from .handlers.wordsearch import WordSearchHandlers

resource_loader = ResourceLoader(__name__)

# Maps each game_type to the handler class responsible for its student_view.
_STUDENT_VIEW_HANDLERS = {
    GameType.MATCHING: MatchingHandlers,
    GameType.SEQUENCING: SequencingHandlers,
    GameType.CLOZE: ClozeHandlers,
    GameType.WORD_SEARCH: WordSearchHandlers,
    GameType.MEMORY: MemoryHandlers,
}


class OpenedxGamesXBlock(XBlock):
    """
    An XBlock offering a small family of interactive games.

    ``game_type`` selects which game this instance renders; each game has its
    own content fields (only the ones relevant to the selected game_type are
    populated by the author) and, for the three graded games, shares a common
    attempts/scoring/grade-publishing flow.
    """

    has_score = True

    # -- Settings, configured by the author in studio_view --------------------

    display_name = String(
        default=Default.DISPLAY_NAME,
        scope=Scope.settings,
        help=_("The display name for this component."),
    )
    game_type = String(
        default=Default.GAME_TYPE,
        scope=Scope.settings,
        help=_("Which game this block renders."),
        values=list(GameType.ALL),
    )
    instructions = String(
        default="",
        scope=Scope.settings,
        help=_("Optional instructions shown to the learner above the game."),
    )
    is_shuffled = Boolean(
        default=Default.IS_SHUFFLED,
        scope=Scope.settings,
        help=_("Whether to shuffle the game content on each render."),
    )
    weight = Float(
        default=Default.WEIGHT,
        scope=Scope.settings,
        help=_("Maximum score for this component, for graded games."),
    )
    max_attempts = Integer(
        default=Default.MAX_ATTEMPTS,
        scope=Scope.settings,
        help=_("Maximum number of graded submission attempts. 0 means unlimited."),
    )
    timer_enabled = Boolean(
        default=Default.TIMER_ENABLED,
        scope=Scope.settings,
        help=_("Whether to show a completion timer (word search / memory only)."),
    )

    # -- Content, authored per game_type ---------------------------------------

    cards = List(
        default=[], scope=Scope.content,
        help=_("Matching game: list of {card_id, term, term_image, definition, definition_image}."),
    )
    sequence_items = List(
        default=[], scope=Scope.content,
        help=_("Sequencing game: list of {item_id, text} in correct order."),
    )
    cloze_text = String(
        default="", scope=Scope.content,
        help=_("Cloze game: passage text containing {{token}} placeholders for each blank."),
    )
    cloze_blanks = List(
        default=[], scope=Scope.content,
        help=_("Cloze game: list of {token, answers, distractors}."),
    )
    wordsearch_words = List(
        default=[], scope=Scope.content,
        help=_("Word search game: list of words to hide in the grid."),
    )
    memory_pairs = List(
        default=[], scope=Scope.content,
        help=_("Memory game: list of {pair_id, a, b}."),
    )

    # -- Per-learner grading state ----------------------------------------------

    attempts = Integer(default=0, scope=Scope.user_state, help=_("Number of graded submissions made."))
    raw_earned = Float(default=0.0, scope=Scope.user_state, help=_("Best raw score (0..weight) across attempts."))
    last_result = Dict(default=None, scope=Scope.user_state, help=_("Per-item verdicts from the most recent attempt."))
    session_key_hex = String(
        default=None, scope=Scope.user_state,
        help=_("Per-render secret used to tag matching/memory answers so the mapping isn't exposed client-side."),
    )

    # -- Per-learner completion state (ungraded games) ---------------------------

    completed = Boolean(default=False, scope=Scope.user_state)
    best_time_seconds = Integer(default=None, scope=Scope.user_state)

    def max_score(self):
        """Return the maximum possible score, required by the XBlock ``has_score`` contract."""
        if self.game_type in GameType.GRADED:
            return self.weight
        return None

    def get_score(self):
        """Return the learner's current best score as a ``{"score": ..., "total": ...}`` dict."""
        if self.game_type not in GameType.GRADED:
            return None
        return {"score": self.raw_earned, "total": self.weight}

    def student_view(self, context=None):
        """Render the primary, student-facing view -- dispatches by ``game_type``."""
        handler_cls = _STUDENT_VIEW_HANDLERS.get(self.game_type, MatchingHandlers)
        return handler_cls.student_view(self, context)

    def studio_view(self, context=None):
        """Render the authoring view: a single editor covering every game type."""
        return CommonHandlers.studio_view(self, context)

    def resource_string(self, path):
        """Read a static resource as text, relative to this package's ``static/`` directory."""
        return resource_loader.load_unicode(f"static/{path}")

    # -- Common handlers (studio authoring) --------------------------------------

    @XBlock.json_handler
    def save_settings(self, data, suffix=""):
        """Persist authored settings and content for the current game_type."""
        return CommonHandlers.save_settings(self, data, suffix)

    @XBlock.handler
    def upload_image(self, request, suffix=""):
        """Upload an image (matching/memory) to Django's default storage and return its URL."""
        return CommonHandlers.upload_image(self, request, suffix)

    # -- Graded-game submit handlers ----------------------------------------------

    @XBlock.json_handler
    def submit_matching(self, data, suffix=""):
        """Score a matching submission, record the attempt, and publish a grade."""
        return MatchingHandlers.submit(self, data, suffix)

    @XBlock.json_handler
    def submit_sequencing(self, data, suffix=""):
        """Score a sequencing submission, record the attempt, and publish a grade."""
        return SequencingHandlers.submit(self, data, suffix)

    @XBlock.json_handler
    def submit_cloze(self, data, suffix=""):
        """Score a cloze submission, record the attempt, and publish a grade."""
        return ClozeHandlers.submit(self, data, suffix)

    # -- Ungraded-game completion handlers -----------------------------------------

    @XBlock.json_handler
    def complete_wordsearch(self, data, suffix=""):
        """Record word-search completion and best time (no grade is published)."""
        return WordSearchHandlers.complete(self, data, suffix)

    @XBlock.json_handler
    def complete_memory(self, data, suffix=""):
        """Record memory-game completion and best time (no grade is published)."""
        return MemoryHandlers.complete(self, data, suffix)

    @staticmethod
    def workbench_scenarios():
        """Canned scenarios for the XBlock SDK workbench, one per game type."""
        return [
            ("Games: Matching", '<openedx_gamesxblock game_type="matching"/>'),
            ("Games: Sequencing", '<openedx_gamesxblock game_type="sequencing"/>'),
            ("Games: Cloze", '<openedx_gamesxblock game_type="cloze"/>'),
            ("Games: Word Search", '<openedx_gamesxblock game_type="word_search"/>'),
            ("Games: Memory", '<openedx_gamesxblock game_type="memory"/>'),
            (
                "Games: all in one unit",
                """<vertical_demo>
                <openedx_gamesxblock game_type="matching"/>
                <openedx_gamesxblock game_type="sequencing"/>
                <openedx_gamesxblock game_type="cloze"/>
                <openedx_gamesxblock game_type="word_search"/>
                <openedx_gamesxblock game_type="memory"/>
                </vertical_demo>
             """,
            ),
        ]
