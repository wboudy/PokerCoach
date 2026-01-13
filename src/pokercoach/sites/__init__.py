"""Site-specific adapters."""

from pokercoach.sites.base import SiteAdapter
from pokercoach.sites.pokerstars import PokerStarsAdapter

__all__ = ["PokerStarsAdapter", "SiteAdapter"]
