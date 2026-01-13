"""Site-specific calibration for vision module."""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import json


@dataclass
class RegionConfig:
    """Configuration for a screen region."""

    x: int
    y: int
    width: int
    height: int
    name: str
    description: str = ""


@dataclass
class SiteCalibration:
    """Calibration data for a poker site."""

    site_name: str
    window_title: str
    table_size: tuple[int, int]  # Expected window dimensions

    # Card regions
    hole_card_region: Optional[RegionConfig] = None
    board_region: Optional[RegionConfig] = None

    # Numeric regions
    pot_region: Optional[RegionConfig] = None
    hero_stack_region: Optional[RegionConfig] = None
    villain_stack_regions: list[RegionConfig] = None

    # Action regions
    action_buttons_region: Optional[RegionConfig] = None

    def __post_init__(self):
        if self.villain_stack_regions is None:
            self.villain_stack_regions = []

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "site_name": self.site_name,
            "window_title": self.window_title,
            "table_size": self.table_size,
            "hole_card_region": self._region_to_dict(self.hole_card_region),
            "board_region": self._region_to_dict(self.board_region),
            "pot_region": self._region_to_dict(self.pot_region),
            "hero_stack_region": self._region_to_dict(self.hero_stack_region),
            "villain_stack_regions": [
                self._region_to_dict(r) for r in self.villain_stack_regions
            ],
            "action_buttons_region": self._region_to_dict(self.action_buttons_region),
        }

    @staticmethod
    def _region_to_dict(region: Optional[RegionConfig]) -> Optional[dict]:
        if region is None:
            return None
        return {
            "x": region.x,
            "y": region.y,
            "width": region.width,
            "height": region.height,
            "name": region.name,
            "description": region.description,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SiteCalibration":
        """Create from dictionary."""
        def dict_to_region(d: Optional[dict]) -> Optional[RegionConfig]:
            if d is None:
                return None
            return RegionConfig(**d)

        return cls(
            site_name=data["site_name"],
            window_title=data["window_title"],
            table_size=tuple(data["table_size"]),
            hole_card_region=dict_to_region(data.get("hole_card_region")),
            board_region=dict_to_region(data.get("board_region")),
            pot_region=dict_to_region(data.get("pot_region")),
            hero_stack_region=dict_to_region(data.get("hero_stack_region")),
            villain_stack_regions=[
                dict_to_region(r) for r in data.get("villain_stack_regions", [])
            ],
            action_buttons_region=dict_to_region(data.get("action_buttons_region")),
        )

    def save(self, path: Path) -> None:
        """Save calibration to JSON file."""
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, path: Path) -> "SiteCalibration":
        """Load calibration from JSON file."""
        with open(path) as f:
            data = json.load(f)
        return cls.from_dict(data)


class CalibrationWizard:
    """Interactive wizard for creating site calibrations."""

    def __init__(self):
        self.current_calibration: Optional[SiteCalibration] = None

    def start_calibration(self, site_name: str, window_title: str) -> None:
        """Start a new calibration session."""
        self.current_calibration = SiteCalibration(
            site_name=site_name,
            window_title=window_title,
            table_size=(0, 0),
        )

    def set_region(
        self,
        region_type: str,
        x: int,
        y: int,
        width: int,
        height: int,
    ) -> None:
        """Set a region in the calibration."""
        if self.current_calibration is None:
            raise RuntimeError("No calibration in progress")

        region = RegionConfig(
            x=x, y=y, width=width, height=height, name=region_type
        )

        if region_type == "hole_cards":
            self.current_calibration.hole_card_region = region
        elif region_type == "board":
            self.current_calibration.board_region = region
        elif region_type == "pot":
            self.current_calibration.pot_region = region
        elif region_type == "hero_stack":
            self.current_calibration.hero_stack_region = region
        elif region_type == "action_buttons":
            self.current_calibration.action_buttons_region = region
        else:
            raise ValueError(f"Unknown region type: {region_type}")

    def finish_calibration(self) -> SiteCalibration:
        """Finish and return the calibration."""
        if self.current_calibration is None:
            raise RuntimeError("No calibration in progress")

        result = self.current_calibration
        self.current_calibration = None
        return result
