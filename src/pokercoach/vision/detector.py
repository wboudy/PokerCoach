"""Card and game element detection."""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np

from pokercoach.core.game_state import Board, Card, Hand


@dataclass
class DetectionResult:
    """Result of card detection."""

    card: Card
    confidence: float
    bbox: tuple[int, int, int, int]  # x, y, width, height


@dataclass
class TableState:
    """Detected state of the poker table."""

    hole_cards: Optional[Hand] = None
    board: Optional[Board] = None
    pot_size: Optional[float] = None
    hero_stack: Optional[float] = None
    villain_stacks: list[float] = None
    bet_sizes: list[float] = None
    action_buttons: list[str] = None

    def __post_init__(self):
        if self.villain_stacks is None:
            self.villain_stacks = []
        if self.bet_sizes is None:
            self.bet_sizes = []
        if self.action_buttons is None:
            self.action_buttons = []


class CardDetector:
    """
    Detect playing cards in screenshots.

    Uses template matching as primary method with VLM fallback.
    """

    def __init__(self, templates_dir: Optional[Path] = None):
        self.templates_dir = templates_dir
        self._templates: dict[str, np.ndarray] = {}
        self._load_templates()

    def _load_templates(self) -> None:
        """Load card template images."""
        if self.templates_dir is None:
            return

        import cv2

        cards_dir = self.templates_dir / "cards"
        if not cards_dir.exists():
            return

        for template_file in cards_dir.glob("*.png"):
            card_name = template_file.stem  # e.g., "As", "Kh"
            self._templates[card_name] = cv2.imread(
                str(template_file), cv2.IMREAD_COLOR
            )

    def detect_card(
        self, image: np.ndarray, threshold: float = 0.8
    ) -> Optional[DetectionResult]:
        """
        Detect a single card in an image region.

        Args:
            image: Image region containing a card
            threshold: Minimum confidence threshold

        Returns:
            DetectionResult or None if no card detected
        """
        import cv2

        best_match: Optional[DetectionResult] = None
        best_confidence = threshold

        for card_name, template in self._templates.items():
            result = cv2.matchTemplate(image, template, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(result)

            if max_val > best_confidence:
                best_confidence = max_val
                h, w = template.shape[:2]
                best_match = DetectionResult(
                    card=Card.from_string(card_name),
                    confidence=max_val,
                    bbox=(max_loc[0], max_loc[1], w, h),
                )

        return best_match

    def detect_cards_in_region(
        self, image: np.ndarray, expected_count: int = 1
    ) -> list[DetectionResult]:
        """
        Detect multiple cards in a region.

        Args:
            image: Image region containing cards
            expected_count: Expected number of cards

        Returns:
            List of detected cards
        """
        # TODO: Implement multi-card detection
        # Use contour detection to find card regions first
        raise NotImplementedError("Multi-card detection not yet implemented")

    def detect_hole_cards(self, image: np.ndarray) -> Optional[Hand]:
        """
        Detect hero's hole cards.

        Args:
            image: Screenshot of poker table

        Returns:
            Hand if detected, None otherwise
        """
        # TODO: Implement hole card region detection
        raise NotImplementedError("Hole card detection not yet implemented")

    def detect_board(self, image: np.ndarray) -> Board:
        """
        Detect community cards on the board.

        Args:
            image: Screenshot of poker table

        Returns:
            Board with detected cards
        """
        # TODO: Implement board detection
        raise NotImplementedError("Board detection not yet implemented")


class OCRExtractor:
    """Extract numeric values from screenshots using OCR."""

    def __init__(self):
        self._reader = None

    def _get_reader(self):
        """Lazy initialization of EasyOCR."""
        if self._reader is None:
            import easyocr

            self._reader = easyocr.Reader(["en"], gpu=False)
        return self._reader

    def extract_number(self, image: np.ndarray) -> Optional[float]:
        """
        Extract a numeric value from an image region.

        Args:
            image: Image region containing a number

        Returns:
            Extracted number or None
        """
        reader = self._get_reader()
        results = reader.readtext(image)

        for _, text, confidence in results:
            # Clean up text and try to parse as number
            cleaned = text.replace(",", "").replace("$", "").replace(" ", "")
            try:
                return float(cleaned)
            except ValueError:
                continue

        return None

    def extract_pot_size(self, image: np.ndarray) -> Optional[float]:
        """Extract pot size from pot region."""
        return self.extract_number(image)

    def extract_stack_size(self, image: np.ndarray) -> Optional[float]:
        """Extract stack size from stack region."""
        return self.extract_number(image)


class TableDetector:
    """
    Full table state detection combining cards and OCR.
    """

    def __init__(self, site_config: dict):
        """
        Initialize with site-specific configuration.

        Args:
            site_config: Dict with region coordinates for the poker site
        """
        self.config = site_config
        self.card_detector = CardDetector()
        self.ocr = OCRExtractor()

    def detect_table_state(self, screenshot: np.ndarray) -> TableState:
        """
        Detect full table state from screenshot.

        Args:
            screenshot: Full screenshot of poker table

        Returns:
            TableState with all detected elements
        """
        # TODO: Implement full detection pipeline
        # 1. Extract hole card region -> detect hole cards
        # 2. Extract board region -> detect board
        # 3. Extract pot region -> OCR pot size
        # 4. Extract stack regions -> OCR stacks
        raise NotImplementedError("Full table detection not yet implemented")
