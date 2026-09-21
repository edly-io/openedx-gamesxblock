"""
Scoring for the cloze (drag-into-blanks) game: one point per blank filled with
an accepted answer.
"""

from ..constants import ClozeField
from .base import ScoreResult


def _normalize(text):
    """Case/whitespace-insensitive comparison so trivial formatting differences don't fail a blank."""
    return (text or "").strip().casefold()


def score_cloze(blanks, submitted_fill):
    """
    Score a cloze-game submission.

    Args:
        blanks: authored answer key, a list of dicts each containing
            ``ClozeField.TOKEN`` (a unique id for the gap) and
            ``ClozeField.ANSWERS`` (a list of one-or-more accepted strings
            for that gap -- allows the author to accept synonyms).
        submitted_fill: dict mapping ``token -> submitted word`` for every
            gap the learner dropped a word into. A gap left empty may be
            omitted or mapped to ``None``/``""``.

    Returns:
        ScoreResult with one ``per_item`` entry per blank:
        ``{"id", "correct", "correct_answer", "submitted_answer"}``. When a
        blank accepts several synonyms, ``correct_answer`` reports the first
        one as the canonical answer shown in the reveal.
    """
    per_item = []
    earned = 0

    for blank in blanks:
        token = blank[ClozeField.TOKEN]
        accepted_answers = blank.get(ClozeField.ANSWERS) or []
        submitted_answer = submitted_fill.get(token)

        is_correct = any(_normalize(submitted_answer) == _normalize(answer) for answer in accepted_answers)
        if is_correct:
            earned += 1

        per_item.append({
            "id": token,
            "correct": is_correct,
            "correct_answer": accepted_answers[0] if accepted_answers else None,
            "submitted_answer": submitted_answer,
        })

    return ScoreResult(raw_earned=earned, raw_possible=len(blanks), per_item=per_item)
