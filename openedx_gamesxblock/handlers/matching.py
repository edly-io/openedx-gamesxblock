"""
Matching game: connect each term to its definition, revealed only after submit.
"""

import hashlib
import hmac
import secrets

from web_fragments.fragment import Fragment
from xblock.utils.resources import ResourceLoader

from ..constants import CardField
from ..scoring.matching import score_matching
from .grading import attempts_remaining, record_attempt_and_publish_grade

resource_loader = ResourceLoader("openedx_gamesxblock")


def _card_hmac(session_key, card_id):
    """
    Derive an opaque tag for a card's definition side, so the DOM never carries
    the real term<->definition mapping before the learner submits.

    The tag is a function of a random-per-render ``session_key`` (never sent to
    the client) and the card's id, so it changes every render and can't be
    reverse-engineered from the page source, yet the server can still verify a
    submitted (term_card_id, definition_tag) pair by recomputing the same tag.
    """
    return hmac.new(session_key, card_id.encode("utf-8"), hashlib.sha256).hexdigest()


class MatchingHandlers:
    """student_view rendering and submit handling for the matching game."""

    @staticmethod
    def student_view(xblock, context=None):  # pylint: disable=unused-argument
        """Render the matching board: two shuffled columns, no answer key exposed."""
        cards = list(xblock.cards)
        session_key = secrets.token_bytes(32)

        term_items = []
        definition_items = []
        for card in cards:
            card_id = card[CardField.CARD_ID]
            tag = _card_hmac(session_key, card_id)
            term_items.append({
                "card_id": card_id,
                "text": card[CardField.TERM],
                "image": card.get(CardField.TERM_IMAGE) or "",
            })
            definition_items.append({
                "tag": tag,
                "card_id_encrypted": tag,  # exposed name in the DOM; never the real card_id
                "text": card[CardField.DEFINITION],
                "image": card.get(CardField.DEFINITION_IMAGE) or "",
            })

        if xblock.is_shuffled:
            secrets.SystemRandom().shuffle(term_items)
            secrets.SystemRandom().shuffle(definition_items)

        # The session_key must survive across the render and the eventual submit
        # call so the server can re-derive tags to check the learner's answer,
        # without ever persisting the plaintext mapping to the client.
        xblock.session_key_hex = session_key.hex()

        html = resource_loader.render_django_template(
            "/static/html/matching.html",
            {
                "display_name": xblock.display_name,
                "instructions": xblock.instructions,
                "term_items": term_items,
                "definition_items": definition_items,
                "has_pairs": bool(cards),
                "max_attempts": xblock.max_attempts,
                "attempts": xblock.attempts,
                "attempts_remaining": attempts_remaining(xblock),
                "already_attempted": xblock.attempts > 0,
                "last_result": xblock.last_result,
            },
        )

        frag = Fragment(html)
        frag.add_css(resource_loader.load_unicode("/static/css/engine.css"))
        frag.add_css(resource_loader.load_unicode("/static/css/matching.css"))
        frag.add_javascript(resource_loader.load_unicode("/static/js/src/engine/arrows.js"))
        frag.add_javascript(resource_loader.load_unicode("/static/js/src/matching.js"))
        frag.initialize_js("GamesXBlockMatching")
        return frag

    @staticmethod
    def submit(xblock, data, suffix=""):  # pylint: disable=unused-argument
        """
        Score a matching submission.

        Expected payload: ``{"pairs": {"<term_card_id>": "<definition_tag>", ...}}``.
        The server resolves each definition_tag back to the card_id it actually
        belongs to (by recomputing the HMAC over the session key stored at
        render time), then scores as normal card_id == card_id matching.
        """
        session_key_hex = getattr(xblock, "session_key_hex", None)
        cards = list(xblock.cards)

        if not session_key_hex:
            # Session expired/never rendered (e.g. stale tab) -- treat every pair as wrong
            # rather than erroring, so the learner still gets a scored (0) result and can retry.
            resolved_pairs = {}
        else:
            session_key = bytes.fromhex(session_key_hex)
            tag_to_card_id = {
                _card_hmac(session_key, card[CardField.CARD_ID]): card[CardField.CARD_ID]
                for card in cards
            }
            submitted_pairs = data.get("pairs") or {}
            resolved_pairs = {
                term_card_id: tag_to_card_id.get(definition_tag)
                for term_card_id, definition_tag in submitted_pairs.items()
            }

        score_result = score_matching(cards, resolved_pairs)
        return record_attempt_and_publish_grade(xblock, score_result)
