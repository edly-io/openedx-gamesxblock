"""
Cloze game: drag words from a bank into blanks in a passage.
"""

import re
import secrets

from web_fragments.fragment import Fragment
from xblock.utils.resources import ResourceLoader

from ..constants import ClozeField
from ..scoring.cloze import score_cloze
from .grading import attempts_remaining, record_attempt_and_publish_grade

resource_loader = ResourceLoader("openedx_gamesxblock")

# Matches the {{token}} placeholders authors embed in cloze_text.
_BLANK_TOKEN_RE = re.compile(r"\{\{\s*(\w+)\s*\}\}")


class ClozeHandlers:
    """student_view rendering and submit handling for the cloze game."""

    @staticmethod
    def _render_passage_segments(text):
        """
        Split ``text`` on ``{{token}}`` placeholders into a list the template can
        walk, alternating literal text segments with blank markers:
        ``[{"type": "text", "value": ...}, {"type": "blank", "token": ...}, ...]``.
        """
        segments = []
        last_end = 0
        for match in _BLANK_TOKEN_RE.finditer(text or ""):
            if match.start() > last_end:
                segments.append({"type": "text", "value": text[last_end:match.start()]})
            segments.append({"type": "blank", "token": match.group(1)})
            last_end = match.end()
        if last_end < len(text or ""):
            segments.append({"type": "text", "value": text[last_end:]})
        return segments

    @staticmethod
    def student_view(xblock, context=None):  # pylint: disable=unused-argument
        """Render the passage with drop-target gaps and a shuffled word bank."""
        segments = ClozeHandlers._render_passage_segments(xblock.cloze_text)

        word_bank = []
        for blank in xblock.cloze_blanks:
            answers = blank.get(ClozeField.ANSWERS) or []
            if answers:
                word_bank.append(answers[0])
            word_bank.extend(blank.get(ClozeField.DISTRACTORS) or [])
        if xblock.is_shuffled:
            secrets.SystemRandom().shuffle(word_bank)

        html = resource_loader.render_django_template(
            "/static/html/cloze.html",
            {
                "display_name": xblock.display_name,
                "instructions": xblock.instructions,
                "segments": segments,
                "word_bank": word_bank,
                "has_blanks": bool(xblock.cloze_blanks),
                "max_attempts": xblock.max_attempts,
                "attempts": xblock.attempts,
                "attempts_remaining": attempts_remaining(xblock),
                "already_attempted": xblock.attempts > 0,
                "last_result": xblock.last_result,
            },
        )

        frag = Fragment(html)
        frag.add_css(resource_loader.load_unicode("/static/css/engine.css"))
        frag.add_css(resource_loader.load_unicode("/static/css/cloze.css"))
        frag.add_javascript(resource_loader.load_unicode("/static/js/src/engine/dnd.js"))
        frag.add_javascript(resource_loader.load_unicode("/static/js/src/cloze.js"))
        frag.initialize_js("GamesXBlockCloze")
        return frag

    @staticmethod
    def submit(xblock, data, suffix=""):  # pylint: disable=unused-argument
        """
        Score a cloze submission.

        Expected payload: ``{"fill": {"<token>": "<submitted word>", ...}}``.
        """
        submitted_fill = data.get("fill") or {}
        score_result = score_cloze(list(xblock.cloze_blanks), submitted_fill)
        return record_attempt_and_publish_grade(xblock, score_result)
