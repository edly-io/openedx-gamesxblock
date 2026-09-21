"""
Constants shared across the Games XBlock: game types, field names, and defaults.
"""


class GameType:
    """Identifiers for each supported game, stored in the ``game_type`` field."""

    MATCHING = "matching"
    SEQUENCING = "sequencing"
    CLOZE = "cloze"
    WORD_SEARCH = "word_search"
    MEMORY = "memory"

    GRADED = (MATCHING, SEQUENCING, CLOZE)
    UNGRADED = (WORD_SEARCH, MEMORY)
    ALL = GRADED + UNGRADED


class CardField:
    """Keys used inside each ``cards`` entry for the matching game."""

    CARD_ID = "card_id"
    TERM = "term"
    TERM_IMAGE = "term_image"
    DEFINITION = "definition"
    DEFINITION_IMAGE = "definition_image"


class SequenceField:
    """Keys used inside each ``sequence_items`` entry."""

    ITEM_ID = "item_id"
    TEXT = "text"


class ClozeField:
    """Keys used inside each ``cloze_blanks`` entry."""

    TOKEN = "token"
    ANSWERS = "answers"
    DISTRACTORS = "distractors"


class MemoryField:
    """Keys used inside each ``memory_pairs`` entry."""

    PAIR_ID = "pair_id"
    A = "a"
    B = "b"


class Default:
    """Default field values."""

    DISPLAY_NAME = "Game"
    GAME_TYPE = GameType.MATCHING
    IS_SHUFFLED = True
    WEIGHT = 1.0
    MAX_ATTEMPTS = 3  # 0 means unlimited attempts
    TIMER_ENABLED = False


class Limits:
    """Sane upper bounds so a bad payload can't cause runaway server work."""

    MAX_ITEMS = 100
    MAX_TEXT_LENGTH = 2000
    MIN_WORD_SEARCH_WORD_LENGTH = 2
    MAX_WORD_SEARCH_GRID_SIZE = 20
