"""
Feature toggles for the Games XBlock.
"""

from edx_toggles.toggles import WaffleFlag

# .. toggle_name: content.experiments.games_xblock
# .. toggle_implementation: WaffleFlag
# .. toggle_default: False
# .. toggle_description: Enables the Games XBlock (matching, sequencing, cloze, word search,
#   memory) so course teams can add it from the Studio "Advanced" component picker.
# .. toggle_use_cases: opt_in
# .. toggle_creation_date: 2026-09-07
ENABLE_GAMES_XBLOCK = WaffleFlag(
    "content.experiments.games_xblock",
    module_name=__name__,
    log_prefix="games_xblock",
)


def is_games_xblock_enabled():
    """
    Return whether the Games XBlock is enabled.

    Guarded with a broad except so a misconfigured or unavailable Waffle
    backend at import/startup time (e.g. during a management command before
    the DB is reachable) can't crash the process -- it simply reports the
    flag as disabled instead.
    """
    try:
        return ENABLE_GAMES_XBLOCK.is_enabled()
    except Exception:  # pylint: disable=broad-except
        return False
