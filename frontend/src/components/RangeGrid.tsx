/**
 * RangeGrid - 13x13 poker range visualization component
 *
 * Displays a hand range matrix with color-coding by action frequency.
 * Shows hero range and optionally villain range side-by-side.
 */

import React from "react";

// Ranks in order from high to low
const RANKS = ["A", "K", "Q", "J", "T", "9", "8", "7", "6", "5", "4", "3", "2"];

// Action type for color coding
type ActionType = "fold" | "call" | "raise" | "check" | "bet" | "all-in";

// Frequency data for a hand in the range
interface HandFrequency {
  hand: string; // e.g., "AA", "AKs", "AKo"
  frequencies: Partial<Record<ActionType, number>>;
  inRange: boolean;
}

// Props for the RangeGrid component
interface RangeGridProps {
  // Range data as a map from hand string to frequencies
  rangeData?: Record<string, HandFrequency>;
  // Optional title for the grid
  title?: string;
  // Callback when a cell is clicked
  onCellClick?: (hand: string, row: number, col: number) => void;
  // Whether to show suited/offsuit labels
  showLabels?: boolean;
  // Color scheme for actions
  colorScheme?: Partial<Record<ActionType, string>>;
  // Size variant
  size?: "small" | "medium" | "large";
}

// Default color scheme
const DEFAULT_COLORS: Record<ActionType, string> = {
  fold: "#dc3545", // Red
  call: "#28a745", // Green
  raise: "#007bff", // Blue
  check: "#6c757d", // Gray
  bet: "#17a2b8", // Cyan
  "all-in": "#ffc107", // Yellow
};

/**
 * Get the hand notation for a cell in the 13x13 grid
 * Row is the first card rank (A-2), col is the second card rank (A-2)
 * Diagonal is pairs, above diagonal is suited, below is offsuit
 */
function getHandNotation(row: number, col: number): string {
  const rank1 = RANKS[row];
  const rank2 = RANKS[col];

  if (row === col) {
    // Pocket pair
    return `${rank1}${rank2}`;
  } else if (row < col) {
    // Above diagonal - suited (higher rank first)
    return `${rank1}${rank2}s`;
  } else {
    // Below diagonal - offsuit (higher rank first)
    return `${rank2}${rank1}o`;
  }
}

/**
 * Get the display text for a cell (abbreviated hand notation)
 */
function getCellDisplay(row: number, col: number): string {
  const rank1 = RANKS[row];
  const rank2 = RANKS[col];

  if (row === col) {
    return `${rank1}${rank2}`;
  } else if (row < col) {
    return `${rank1}${rank2}s`;
  } else {
    return `${rank2}${rank1}o`;
  }
}

/**
 * Calculate the background color based on action frequencies
 */
function getBackgroundColor(
  frequencies: Partial<Record<ActionType, number>> | undefined,
  colorScheme: Record<ActionType, string>
): string {
  if (!frequencies) {
    return "transparent";
  }

  // Find the dominant action
  let maxFreq = 0;
  let dominantAction: ActionType | null = null;

  for (const [action, freq] of Object.entries(frequencies)) {
    if (freq && freq > maxFreq) {
      maxFreq = freq;
      dominantAction = action as ActionType;
    }
  }

  if (!dominantAction || maxFreq === 0) {
    return "transparent";
  }

  // Get base color and adjust opacity based on frequency
  const baseColor = colorScheme[dominantAction];
  const opacity = Math.max(0.2, maxFreq);

  return `${baseColor}${Math.round(opacity * 255).toString(16).padStart(2, "0")}`;
}

/**
 * RangeCell - Individual cell in the range grid
 */
interface RangeCellProps {
  row: number;
  col: number;
  handData?: HandFrequency;
  colorScheme: Record<ActionType, string>;
  onClick?: (hand: string, row: number, col: number) => void;
  size: "small" | "medium" | "large";
}

const RangeCell: React.FC<RangeCellProps> = ({
  row,
  col,
  handData,
  colorScheme,
  onClick,
  size,
}) => {
  const hand = getHandNotation(row, col);
  const display = getCellDisplay(row, col);
  const bgColor = getBackgroundColor(handData?.frequencies, colorScheme);
  const inRange = handData?.inRange ?? false;

  // Size-based styling
  const sizeStyles = {
    small: { width: "28px", height: "28px", fontSize: "10px" },
    medium: { width: "36px", height: "36px", fontSize: "12px" },
    large: { width: "44px", height: "44px", fontSize: "14px" },
  };

  const cellStyle: React.CSSProperties = {
    ...sizeStyles[size],
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: bgColor,
    border: inRange ? "2px solid #000" : "1px solid #ccc",
    borderRadius: "2px",
    cursor: onClick ? "pointer" : "default",
    fontWeight: inRange ? "bold" : "normal",
    opacity: inRange ? 1 : 0.5,
  };

  const handleClick = () => {
    if (onClick) {
      onClick(hand, row, col);
    }
  };

  return (
    <div
      data-testid={`range-cell-${row}-${col}`}
      data-hand={hand}
      style={cellStyle}
      onClick={handleClick}
      title={hand}
    >
      {display}
    </div>
  );
};

/**
 * RangeLegend - Legend showing action colors
 */
const RangeLegend: React.FC<{ colorScheme: Record<ActionType, string> }> = ({
  colorScheme,
}) => {
  const legendItems: ActionType[] = ["fold", "call", "raise", "bet", "all-in"];

  return (
    <div
      data-testid="range-legend"
      style={{
        display: "flex",
        gap: "12px",
        marginTop: "8px",
        flexWrap: "wrap",
      }}
    >
      {legendItems.map((action) => (
        <div
          key={action}
          style={{
            display: "flex",
            alignItems: "center",
            gap: "4px",
          }}
        >
          <div
            style={{
              width: "16px",
              height: "16px",
              backgroundColor: colorScheme[action],
              borderRadius: "2px",
            }}
          />
          <span style={{ fontSize: "12px", textTransform: "capitalize" }}>
            {action}
          </span>
        </div>
      ))}
    </div>
  );
};

/**
 * Main RangeGrid component
 */
export const RangeGrid: React.FC<RangeGridProps> = ({
  rangeData = {},
  title,
  onCellClick,
  showLabels = true,
  colorScheme = {},
  size = "medium",
}) => {
  const mergedColorScheme = { ...DEFAULT_COLORS, ...colorScheme };

  return (
    <div data-testid="range-grid" className="range-grid-container">
      {title && (
        <h3 data-testid="range-title" style={{ marginBottom: "8px" }}>
          {title}
        </h3>
      )}

      <div
        style={{
          display: "grid",
          gridTemplateColumns: `repeat(13, auto)`,
          gap: "2px",
        }}
      >
        {RANKS.map((_, rowIndex) =>
          RANKS.map((_, colIndex) => {
            const hand = getHandNotation(rowIndex, colIndex);
            return (
              <RangeCell
                key={`${rowIndex}-${colIndex}`}
                row={rowIndex}
                col={colIndex}
                handData={rangeData[hand]}
                colorScheme={mergedColorScheme}
                onClick={onCellClick}
                size={size}
              />
            );
          })
        )}
      </div>

      {showLabels && <RangeLegend colorScheme={mergedColorScheme} />}
    </div>
  );
};

/**
 * RangeComparison - Side-by-side comparison of two ranges
 */
interface RangeComparisonProps {
  heroRange?: Record<string, HandFrequency>;
  villainRange?: Record<string, HandFrequency>;
  heroTitle?: string;
  villainTitle?: string;
  size?: "small" | "medium" | "large";
}

export const RangeComparison: React.FC<RangeComparisonProps> = ({
  heroRange = {},
  villainRange = {},
  heroTitle = "Hero Range",
  villainTitle = "Villain Range",
  size = "medium",
}) => {
  return (
    <div
      data-testid="range-comparison"
      style={{
        display: "flex",
        gap: "24px",
        flexWrap: "wrap",
        justifyContent: "center",
      }}
    >
      <RangeGrid rangeData={heroRange} title={heroTitle} size={size} />
      <RangeGrid rangeData={villainRange} title={villainTitle} size={size} />
    </div>
  );
};

// Utility function to convert a simple range string to HandFrequency data
export function parseRangeString(
  rangeStr: string
): Record<string, HandFrequency> {
  const result: Record<string, HandFrequency> = {};

  if (!rangeStr) return result;

  const hands = rangeStr.split(",").map((h) => h.trim());

  for (const hand of hands) {
    if (!hand) continue;

    // Handle frequency notation like "AA:0.5"
    const [handNotation, freqStr] = hand.split(":");
    const frequency = freqStr ? parseFloat(freqStr) : 1.0;

    result[handNotation] = {
      hand: handNotation,
      frequencies: { raise: frequency },
      inRange: true,
    };
  }

  return result;
}

export default RangeGrid;
