"""
Word search: an ungraded, completion-only game. The grid is generated
server-side per render so the solution can't be read out of client-side code.
"""

import random

from web_fragments.fragment import Fragment
from xblock.utils.resources import ResourceLoader

from ..constants import Limits

resource_loader = ResourceLoader("openedx_gamesxblock")

_DIRECTIONS = [
    (0, 1), (1, 0), (1, 1), (-1, 1),   # right, down, diag-down-right, diag-up-right
    (0, -1), (-1, 0), (-1, -1), (1, -1),
]


def _build_grid(words, rng):
    """
    Place every word into a square letter grid, choosing a grid size large
    enough to fit the longest word plus some margin, then filling unused cells
    with random letters. Placement is best-effort: if a word can't be placed
    after a bounded number of attempts (e.g. pathological overlaps), it's
    skipped rather than looping forever.
    """
    cleaned_words = [w.strip().upper() for w in words if w and w.strip()]
    if not cleaned_words:
        return {"size": 0, "rows": [], "placed_words": []}

    longest = max(len(w) for w in cleaned_words)
    size = min(Limits.MAX_WORD_SEARCH_GRID_SIZE, max(longest + 2, 8))

    grid = [[None] * size for _ in range(size)]
    placed_words = []

    for word in cleaned_words:
        if len(word) > size:
            continue  # word too long to ever fit this grid; skip rather than resize mid-build

        # If no placement attempt below succeeds, the word is simply omitted
        # from this render rather than aborting or resizing the whole grid.
        for _attempt in range(200):
            dr, dc = rng.choice(_DIRECTIONS)
            max_row = size - (len(word) - 1) * dr if dr > 0 else size
            min_row = -((len(word) - 1) * dr) if dr < 0 else 0
            max_col = size - (len(word) - 1) * dc if dc > 0 else size
            min_col = -((len(word) - 1) * dc) if dc < 0 else 0
            if min_row >= max_row or min_col >= max_col:
                continue
            start_row = rng.randrange(min_row, max_row)
            start_col = rng.randrange(min_col, max_col)

            cells = [(start_row + i * dr, start_col + i * dc) for i in range(len(word))]
            if all(0 <= r < size and 0 <= c < size for r, c in cells):
                if all(grid[r][c] is None or grid[r][c] == word[i] for i, (r, c) in enumerate(cells)):
                    for i, (r, c) in enumerate(cells):
                        grid[r][c] = word[i]
                    placed_words.append({"word": word, "cells": cells})
                    break

    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    for r in range(size):
        for c in range(size):
            if grid[r][c] is None:
                grid[r][c] = rng.choice(alphabet)

    return {"size": size, "rows": grid, "placed_words": placed_words}


class WordSearchHandlers:
    """student_view rendering and completion handling for the word search game."""

    @staticmethod
    def student_view(xblock, context=None):  # pylint: disable=unused-argument
        """Render a freshly generated grid containing every authored word."""
        rng = random.Random()  # nosec B311 -- puzzle layout, not security-sensitive
        grid = _build_grid(list(xblock.wordsearch_words), rng)

        # Pre-format each word's cell coordinates as "r-c,r-c,..." so the template
        # can emit a plain string attribute rather than a Python list repr.
        placed_words = [
            {"word": entry["word"], "cells_attr": ",".join(f"{r}-{c}" for r, c in entry["cells"])}
            for entry in grid["placed_words"]
        ]

        html = resource_loader.render_django_template(
            "/static/html/wordsearch.html",
            {
                "display_name": xblock.display_name,
                "instructions": xblock.instructions,
                "grid_size": grid["size"],
                "grid_rows": grid["rows"],
                "placed_words": placed_words,
                "has_words": bool(placed_words),
                "timer_enabled": xblock.timer_enabled,
                "best_time_seconds": xblock.best_time_seconds,
            },
        )

        frag = Fragment(html)
        frag.add_css(resource_loader.load_unicode("/static/css/engine.css"))
        frag.add_css(resource_loader.load_unicode("/static/css/wordsearch.css"))
        frag.add_javascript(resource_loader.load_unicode("/static/js/src/wordsearch.js"))
        frag.initialize_js("GamesXBlockWordSearch")
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
