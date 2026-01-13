"""Base site adapter interface."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

import numpy as np

from pokercoach.vision.calibration import SiteCalibration
from pokercoach.vision.detector import TableState


@dataclass
class SiteInfo:
    """Information about a poker site."""

    name: str
    window_title_pattern: str
    supports_hand_history: bool = True
    hh_directory: Optional[str] = None


class SiteAdapter(ABC):
    """
    Abstract adapter for poker site integration.

    Each site has different:
    - Window appearance
    - Card designs
    - HH format
    - Screen regions
    """

    @property
    @abstractmethod
    def info(self) -> SiteInfo:
        """Get site information."""
        pass

    @property
    @abstractmethod
    def calibration(self) -> SiteCalibration:
        """Get site calibration data."""
        pass

    @abstractmethod
    def detect_table(self, screenshot: np.ndarray) -> Optional[TableState]:
        """
        Detect table state from screenshot.

        Args:
            screenshot: Screenshot of poker table

        Returns:
            TableState or None if detection fails
        """
        pass

    @abstractmethod
    def find_window(self) -> Optional[str]:
        """
        Find poker client window.

        Returns:
            Window title if found, None otherwise
        """
        pass

    def is_table_window(self, window_title: str) -> bool:
        """Check if a window title matches this site's pattern."""
        import re
        return bool(re.search(self.info.window_title_pattern, window_title))
