"""PokerStars site adapter."""

from typing import Optional

import numpy as np

from pokercoach.sites.base import SiteAdapter, SiteInfo
from pokercoach.vision.calibration import RegionConfig, SiteCalibration
from pokercoach.vision.detector import TableState


class PokerStarsAdapter(SiteAdapter):
    """Adapter for PokerStars poker client."""

    @property
    def info(self) -> SiteInfo:
        return SiteInfo(
            name="PokerStars",
            window_title_pattern=r".*PokerStars.*",
            supports_hand_history=True,
            hh_directory="~/AppData/Local/PokerStars/HandHistory",
        )

    @property
    def calibration(self) -> SiteCalibration:
        """
        Default calibration for PokerStars.

        These values are approximate and should be adjusted
        via the calibration wizard for your specific setup.
        """
        return SiteCalibration(
            site_name="PokerStars",
            window_title="PokerStars",
            table_size=(800, 600),  # Standard table size
            hole_card_region=RegionConfig(
                x=350,
                y=400,
                width=100,
                height=70,
                name="hole_cards",
                description="Hero's hole cards",
            ),
            board_region=RegionConfig(
                x=250,
                y=220,
                width=300,
                height=70,
                name="board",
                description="Community cards",
            ),
            pot_region=RegionConfig(
                x=350,
                y=180,
                width=100,
                height=30,
                name="pot",
                description="Pot size display",
            ),
            hero_stack_region=RegionConfig(
                x=350,
                y=470,
                width=100,
                height=25,
                name="hero_stack",
                description="Hero's stack size",
            ),
        )

    def detect_table(self, screenshot: np.ndarray) -> Optional[TableState]:
        """Detect table state from PokerStars screenshot."""
        # TODO: Implement PokerStars-specific detection
        # Use calibration regions to extract elements
        raise NotImplementedError(
            "PokerStars table detection not yet implemented. "
            "Use the calibration wizard to set up regions."
        )

    def find_window(self) -> Optional[str]:
        """Find PokerStars window."""
        # TODO: Implement window detection
        raise NotImplementedError("Window detection not yet implemented")
