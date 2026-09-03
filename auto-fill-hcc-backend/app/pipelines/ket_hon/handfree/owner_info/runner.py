"""Compatibility exports for the shared Justice owner-page runner."""

from app.channels.handfree.owner_info.runner import (
    _detailed_address,
    _digits,
    _field_map,
    _fold,
    _owner_issue_place,
    owner_matches,
    run,
    runner,
)

__all__ = ["owner_matches", "run", "runner"]
