"""
Scoring for the matching game: one point per term correctly paired with its definition.
"""

from ..constants import CardField
from .base import ScoreResult


def score_matching(cards, submitted_pairs):
    """
    Score a matching-game submission.

    Args:
        cards: the authored answer key, a list of dicts each containing at
            least ``CardField.CARD_ID``, ``CardField.TERM`` and
            ``CardField.DEFINITION``.
        submitted_pairs: dict mapping ``card_id -> submitted_card_id``, where
            the key is the term's card and the value is the card whose
            definition the learner connected it to. A term left unconnected
            may be omitted or mapped to ``None``.

    Returns:
        ScoreResult with one ``per_item`` entry per authored card:
        ``{"id", "term", "correct", "correct_answer", "submitted_answer"}``.
    """
    per_item = []
    earned = 0
    cards_by_id = {card[CardField.CARD_ID]: card for card in cards}

    for card in cards:
        card_id = card[CardField.CARD_ID]
        submitted_id = submitted_pairs.get(card_id)
        is_correct = submitted_id == card_id  # a term matches its own definition slot
        if is_correct:
            earned += 1

        submitted_definition = None
        if submitted_id and submitted_id in cards_by_id:
            submitted_definition = cards_by_id[submitted_id][CardField.DEFINITION]

        per_item.append({
            "id": card_id,
            "correct": is_correct,
            "term": card[CardField.TERM],
            "correct_answer": card[CardField.DEFINITION],
            "submitted_answer": submitted_definition,
        })

    return ScoreResult(raw_earned=earned, raw_possible=len(cards), per_item=per_item)
