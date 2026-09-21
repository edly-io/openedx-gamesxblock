"""
Pure, runtime-independent scoring functions for each graded game type.

Every function here takes plain Python data in and returns a :class:`ScoreResult` --
no XBlock, no request, no database. That keeps grading logic trivially unit-testable
and reusable from both the submit handlers and the test suite.
"""

from .base import ScoreResult

__all__ = ["ScoreResult"]
