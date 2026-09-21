"""
Shared result type returned by every game's scoring function.
"""

from dataclasses import dataclass, field


@dataclass
class ScoreResult:
    """
    The outcome of scoring one submitted attempt.

    ``raw_earned`` and ``raw_possible`` are counted in "items" (one point per
    correctly matched pair / correctly placed step / correctly filled blank),
    *not* in the XBlock's weighted score -- the caller is responsible for
    scaling ``raw_earned / raw_possible`` by the block's configured ``weight``.

    ``per_item`` is a list of JSON-serializable dicts describing the verdict
    for each submitted item, in a shape the relevant front-end can render as
    a reveal (e.g. ``{"id": ..., "correct": bool, "correct_answer": ...}``).
    Games decide their own per-item shape; scoring only guarantees that each
    entry has at least an ``"id"`` and a ``"correct"`` key.
    """

    raw_earned: float
    raw_possible: float
    per_item: list = field(default_factory=list)

    @property
    def fraction(self) -> float:
        """Return earned/possible as a 0..1 fraction, guarding against divide-by-zero."""
        if self.raw_possible <= 0:
            return 0.0
        return max(0.0, min(1.0, self.raw_earned / self.raw_possible))

    def to_dict(self) -> dict:
        """Serialize for inclusion in a JSON handler response."""
        return {
            "raw_earned": self.raw_earned,
            "raw_possible": self.raw_possible,
            "fraction": self.fraction,
            "per_item": self.per_item,
        }
