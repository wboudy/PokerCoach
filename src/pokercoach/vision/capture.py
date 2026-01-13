"""Screen capture abstraction."""

from dataclasses import dataclass
from typing import Callable, Optional

import numpy as np


@dataclass
class CaptureRegion:
    """A region of the screen to capture."""

    x: int
    y: int
    width: int
    height: int


class ScreenCapture:
    """
    Cross-platform screen capture using mss.

    Provides fast screen capture for poker client monitoring.
    """

    def __init__(self):
        self._sct = None

    def _get_sct(self):
        """Lazy initialization of mss."""
        if self._sct is None:
            import mss

            self._sct = mss.mss()
        return self._sct

    def capture_full_screen(self, monitor: int = 1) -> np.ndarray:
        """
        Capture entire screen.

        Args:
            monitor: Monitor index (1-based)

        Returns:
            numpy array of screenshot (BGRA format)
        """
        sct = self._get_sct()
        screenshot = sct.grab(sct.monitors[monitor])
        return np.array(screenshot)

    def capture_region(self, region: CaptureRegion) -> np.ndarray:
        """
        Capture a specific region of the screen.

        Args:
            region: Region to capture

        Returns:
            numpy array of screenshot
        """
        sct = self._get_sct()
        monitor = {
            "left": region.x,
            "top": region.y,
            "width": region.width,
            "height": region.height,
        }
        screenshot = sct.grab(monitor)
        return np.array(screenshot)

    def capture_window(self, window_title: str) -> Optional[np.ndarray]:
        """
        Capture a specific window by title.

        Args:
            window_title: Window title to search for

        Returns:
            numpy array of screenshot or None if window not found
        """
        # TODO: Implement window detection by title
        # Platform-specific: use pywin32 on Windows, Quartz on macOS
        raise NotImplementedError("Window capture not yet implemented")

    def list_windows(self) -> list[str]:
        """List all visible window titles."""
        # TODO: Implement window enumeration
        raise NotImplementedError("Window listing not yet implemented")

    def monitor_changes(
        self,
        region: CaptureRegion,
        callback: Callable[[np.ndarray], None],
        threshold: float = 0.01,
        interval_ms: int = 100,
    ) -> None:
        """
        Monitor a region for changes and call callback when detected.

        Args:
            region: Region to monitor
            callback: Function to call with new screenshot
            threshold: Minimum change ratio to trigger callback
            interval_ms: Polling interval in milliseconds
        """
        import time

        import cv2

        prev_frame = None

        while True:
            frame = self.capture_region(region)

            if prev_frame is not None:
                # Calculate frame difference
                gray_curr = cv2.cvtColor(frame, cv2.COLOR_BGRA2GRAY)
                gray_prev = cv2.cvtColor(prev_frame, cv2.COLOR_BGRA2GRAY)
                diff = cv2.absdiff(gray_curr, gray_prev)
                change_ratio = np.count_nonzero(diff > 30) / diff.size

                if change_ratio > threshold:
                    callback(frame)

            prev_frame = frame
            time.sleep(interval_ms / 1000)
