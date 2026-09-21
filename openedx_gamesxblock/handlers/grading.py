"""
Shared attempt-tracking / best-score / grade-publishing flow used by every
graded game's submit handler (matching, sequencing, cloze).

Keeping this in one place guarantees the three games treat "attempts left",
"keep the best score across retries", and "publish a grade event" identically,
so a change to that policy only needs to happen once.
"""

from django.utils.translation import gettext as _
from xblock.exceptions import JsonHandlerError


def attempts_remaining(xblock):
    """Return True if the learner may still submit (0/blank max_attempts means unlimited)."""
    if not xblock.max_attempts:
        return True
    return xblock.attempts < xblock.max_attempts


def record_attempt_and_publish_grade(xblock, score_result):
    """
    Apply one graded attempt's result to the block's persisted state.

    - Rejects the attempt with a 403 JsonHandlerError if no attempts remain.
    - Increments ``attempts``.
    - Keeps ``raw_earned`` as the *best* fraction-of-weight seen across all
      attempts (never lets a worse retry lower the learner's score).
    - Publishes a ``grade`` event with the best score so far, every attempt --
      even one that isn't a new best -- so the gradebook always reflects the
      current best_earned/weight, not a stale value from a prior sync issue.
    - Stores the latest attempt's per-item verdicts in ``last_result`` so the
      reveal can be re-shown (e.g. on page reload) without resubmitting.

    Returns the dict the submit handler should send back to the client.
    """
    if not attempts_remaining(xblock):
        raise JsonHandlerError(403, _("No attempts remaining."))

    xblock.attempts += 1

    new_earned_weighted = score_result.fraction * xblock.weight
    is_new_best = new_earned_weighted > xblock.raw_earned
    if is_new_best:
        xblock.raw_earned = new_earned_weighted

    xblock.last_result = score_result.to_dict()

    xblock.runtime.publish(xblock, "grade", {
        "value": xblock.raw_earned,
        "max_value": xblock.weight,
    })

    return {
        "success": True,
        "per_item": score_result.per_item,
        "raw_earned": score_result.raw_earned,
        "raw_possible": score_result.raw_possible,
        "fraction": score_result.fraction,
        "is_new_best": is_new_best,
        "best_score": xblock.raw_earned,
        "weight": xblock.weight,
        "attempts": xblock.attempts,
        "max_attempts": xblock.max_attempts,
        "attempts_remaining": (
            None if not xblock.max_attempts else max(0, xblock.max_attempts - xblock.attempts)
        ),
    }
