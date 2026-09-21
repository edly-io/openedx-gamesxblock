"""
Scoring for the sequencing game: partial credit via longest-common-subsequence
against the correct order, rather than naive exact-position comparison.

Exact-position scoring would zero out every item after a single displaced one
(e.g. inserting an extra step at the front turns a perfect ordering into a 0/N
score). LCS instead credits every item that is already in correct *relative*
order relative to the others, which matches how a human grader would look at
a shuffled sequence: "these five are in the right order; only this one item is
out of place."
"""

from .base import ScoreResult


def _longest_increasing_run_ids(positions):
    """
    Given a list of correct-position indices (in submission order), return the
    set of list-indices belonging to a longest strictly-increasing subsequence.

    This is the classic O(n log n) patience-sorting LIS, but we track indices
    (not just the length) so callers can mark exactly which submitted items
    are "correctly placed relative to each other".
    """
    if not positions:
        return set()

    # tails[k] = index into `positions` of the smallest tail value for an
    # increasing subsequence of length k + 1.
    tails = []
    # predecessor[i] = index into `positions` of the item preceding `positions[i]`
    # in the increasing subsequence ending at i.
    predecessor = [-1] * len(positions)

    for i, value in enumerate(positions):
        lo, hi = 0, len(tails)
        while lo < hi:
            mid = (lo + hi) // 2
            if positions[tails[mid]] < value:
                lo = mid + 1
            else:
                hi = mid
        if lo > 0:
            predecessor[i] = tails[lo - 1]
        if lo == len(tails):
            tails.append(i)
        else:
            tails[lo] = i

    result = set()
    k = tails[-1] if tails else -1
    while k != -1:
        result.add(k)
        k = predecessor[k]
    return result


def score_sequencing(correct_order, submitted_order):
    """
    Score a sequencing-game submission.

    Args:
        correct_order: list of item_ids in the authored correct order.
        submitted_order: list of item_ids in the order the learner arranged
            them. Must be a permutation of ``correct_order`` for a meaningful
            score; unknown ids are treated as always-incorrect and excluded
            from the increasing-subsequence computation.

    Returns:
        ScoreResult with one ``per_item`` entry per submitted item:
        ``{"id", "correct", "submitted_position", "correct_position"}``.
        ``raw_earned`` is the size of the longest run of items already in
        correct relative order to each other (an item can only be "correct"
        if it also sits in its exact authored slot within that run).
    """
    correct_index = {item_id: idx for idx, item_id in enumerate(correct_order)}
    positions = [correct_index.get(item_id, -1) for item_id in submitted_order]

    # Items not present in the answer key can never contribute to the LIS.
    valid_indices = [i for i, pos in enumerate(positions) if pos != -1]
    valid_positions = [positions[i] for i in valid_indices]
    lis_local_indices = _longest_increasing_run_ids(valid_positions)
    correct_submission_indices = {valid_indices[i] for i in lis_local_indices}

    per_item = []
    earned = 0
    for submitted_idx, item_id in enumerate(submitted_order):
        is_correct = (
            submitted_idx in correct_submission_indices
            and positions[submitted_idx] == submitted_idx
        )
        if is_correct:
            earned += 1
        per_item.append({
            "id": item_id,
            "correct": is_correct,
            "submitted_position": submitted_idx,
            "correct_position": correct_index.get(item_id),
        })

    return ScoreResult(raw_earned=earned, raw_possible=len(correct_order), per_item=per_item)
