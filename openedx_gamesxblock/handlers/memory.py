"""
Memory / concentration: an ungraded, completion-only game. Flip two cards to
find matching pairs; card identities are HMAC-tagged so they can't be read
from the DOM before being flipped, mirroring the matching game's anti-leak
approach.
"""

import hashlib
import hmac
import json
import secrets

from django.utils.safestring import mark_safe
from web_fragments.fragment import Fragment
from xblock.utils.resources import ResourceLoader

from ..constants import MemoryField

resource_loader = ResourceLoader("openedx_gamesxblock")


def _pair_hmac(session_key, pair_id, side):
    """Derive an opaque per-card tag from the pair id and which side ('a'/'b') this card is."""
    return hmac.new(session_key, f"{pair_id}:{side}".encode("utf-8"), hashlib.sha256).hexdigest()


class MemoryHandlers:
    """student_view rendering and completion handling for the memory game."""

    @staticmethod
    def student_view(xblock, context=None):  # pylint: disable=unused-argument
        """Render a shuffled grid of face-down cards, two per authored pair."""
        pairs = list(xblock.memory_pairs)
        # This session key is used only to derive this render's card tags; unlike
        # the matching game, memory needs no server-side submit/verify round trip
        # (it's ungraded), so the key itself is never persisted.
        session_key = secrets.token_bytes(32)

        cards = []
        for pair in pairs:
            pair_id = pair[MemoryField.PAIR_ID]
            cards.append({"tag": _pair_hmac(session_key, pair_id, "a"), "text": pair[MemoryField.A]})
            cards.append({"tag": _pair_hmac(session_key, pair_id, "b"), "text": pair[MemoryField.B]})
        secrets.SystemRandom().shuffle(cards)

        # The server tells the client which tags belong to the same pair (without
        # revealing card *content*), so a correct-match check can happen entirely
        # client-side for instant flip feedback -- this game is ungraded, so
        # there's no integrity requirement beyond "don't show content pre-flip".
        tag_pair_lookup = {}
        for pair in pairs:
            pair_id = pair[MemoryField.PAIR_ID]
            tag_a = _pair_hmac(session_key, pair_id, "a")
            tag_b = _pair_hmac(session_key, pair_id, "b")
            tag_pair_lookup[tag_a] = tag_b
            tag_pair_lookup[tag_b] = tag_a

        # Server-generated JSON (never user input), safe to mark as such for direct embedding.
        tag_pair_lookup_json = mark_safe(json.dumps(tag_pair_lookup))  # noqa: S308

        html = resource_loader.render_django_template(
            "/static/html/memory.html",
            {
                "display_name": xblock.display_name,
                "instructions": xblock.instructions,
                "cards": cards,
                "tag_pair_lookup_json": tag_pair_lookup_json,
                "has_pairs": bool(pairs),
                "timer_enabled": xblock.timer_enabled,
                "best_time_seconds": xblock.best_time_seconds,
            },
        )

        frag = Fragment(html)
        frag.add_css(resource_loader.load_unicode("/static/css/engine.css"))
        frag.add_css(resource_loader.load_unicode("/static/css/memory.css"))
        frag.add_javascript(resource_loader.load_unicode("/static/js/src/memory.js"))
        frag.initialize_js("GamesXBlockMemory")
        return frag

    @staticmethod
    def complete(xblock, data, suffix=""):  # pylint: disable=unused-argument
        """Record completion and keep the best time; no grade is published (ungraded game)."""
        time_seconds = data.get("time_seconds")
        xblock.completed = True

        is_new_best = False
        if isinstance(time_seconds, (int, float)) and time_seconds >= 0:
            if xblock.best_time_seconds is None or time_seconds < xblock.best_time_seconds:
                xblock.best_time_seconds = int(time_seconds)
                is_new_best = True

        return {
            "success": True,
            "completed": True,
            "best_time_seconds": xblock.best_time_seconds,
            "is_new_best": is_new_best,
        }
