"""
Sequencing game: drag a shuffled list of steps into the correct order.
"""

import secrets

from web_fragments.fragment import Fragment
from xblock.utils.resources import ResourceLoader

from ..constants import SequenceField
from ..scoring.sequencing import score_sequencing
from .grading import attempts_remaining, record_attempt_and_publish_grade

resource_loader = ResourceLoader("openedx_gamesxblock")


class SequencingHandlers:
    """student_view rendering and submit handling for the sequencing game."""

    @staticmethod
    def student_view(xblock, context=None):  # pylint: disable=unused-argument
        """Render the sequencing board with items shuffled (the correct order is never sent)."""
        items = [
            {"item_id": item[SequenceField.ITEM_ID], "text": item[SequenceField.TEXT]}
            for item in xblock.sequence_items
        ]
        if xblock.is_shuffled:
            secrets.SystemRandom().shuffle(items)

        html = resource_loader.render_django_template(
            "/static/html/sequencing.html",
            {
                "display_name": xblock.display_name,
                "instructions": xblock.instructions,
                "items": items,
                "has_items": bool(items),
                "max_attempts": xblock.max_attempts,
                "attempts": xblock.attempts,
                "attempts_remaining": attempts_remaining(xblock),
                "already_attempted": xblock.attempts > 0,
                "last_result": xblock.last_result,
            },
        )

        frag = Fragment(html)
        frag.add_css(resource_loader.load_unicode("/static/css/engine.css"))
        frag.add_css(resource_loader.load_unicode("/static/css/sequencing.css"))
        frag.add_javascript(resource_loader.load_unicode("/static/js/src/engine/dnd.js"))
        frag.add_javascript(resource_loader.load_unicode("/static/js/src/sequencing.js"))
        frag.initialize_js("GamesXBlockSequencing")
        return frag

    @staticmethod
    def submit(xblock, data, suffix=""):  # pylint: disable=unused-argument
        """
        Score a sequencing submission.

        Expected payload: ``{"order": ["<item_id>", "<item_id>", ...]}`` listing
        every item_id in the order the learner arranged them.
        """
        correct_order = [item[SequenceField.ITEM_ID] for item in xblock.sequence_items]
        submitted_order = data.get("order") or []

        score_result = score_sequencing(correct_order, submitted_order)
        return record_attempt_and_publish_grade(xblock, score_result)
