/**
 * EVChart - Bar chart comparing EV of available poker actions
 *
 * Displays expected value comparison for fold/call/raise actions.
 * Shows both GTO frequencies and recommended exploit adjustments.
 */

import React from "react";

// Action types for poker decisions
type ActionType = "fold" | "check" | "call" | "bet" | "raise" | "all-in";

// EV data for a single action
interface ActionEV {
  action: ActionType;
  ev: number; // Expected value in BB
  gtoFrequency: number; // GTO frequency (0-1)
  exploitFrequency?: number; // Recommended exploit frequency (0-1)
}

// Props for the EVChart component
interface EVChartProps {
  // EV data for each available action
  actions: ActionEV[];
  // Optional title for the chart
  title?: string;
  // Whether to show exploit adjustments
  showExploit?: boolean;
  // Callback when an action bar is clicked
  onActionClick?: (action: ActionType) => void;
  // Custom bar colors
  barColor?: string;
  exploitBarColor?: string;
  // Chart dimensions
  width?: number;
  height?: number;
}

// Default colors
const DEFAULT_BAR_COLOR = "#007bff";
const DEFAULT_EXPLOIT_COLOR = "#28a745";
const NEGATIVE_COLOR = "#dc3545";

/**
 * Format EV value for display
 */
function formatEV(ev: number): string {
  const sign = ev >= 0 ? "+" : "";
  return `${sign}${ev.toFixed(2)} BB`;
}

/**
 * Format frequency as percentage
 */
function formatFrequency(freq: number): string {
  return `${(freq * 100).toFixed(0)}%`;
}

/**
 * Get bar color based on EV value
 */
function getBarColor(ev: number, defaultColor: string): string {
  return ev >= 0 ? defaultColor : NEGATIVE_COLOR;
}

/**
 * Single action bar component
 */
interface ActionBarProps {
  action: ActionEV;
  maxAbsEV: number;
  showExploit: boolean;
  barColor: string;
  exploitBarColor: string;
  onActionClick?: (action: ActionType) => void;
  width: number;
}

const ActionBar: React.FC<ActionBarProps> = ({
  action,
  maxAbsEV,
  showExploit,
  barColor,
  exploitBarColor,
  onActionClick,
  width,
}) => {
  // Calculate bar widths relative to max EV
  const evBarWidth = maxAbsEV > 0 ? (Math.abs(action.ev) / maxAbsEV) * 100 : 0;
  const gtoBarWidth = action.gtoFrequency * 100;
  const exploitBarWidth = (action.exploitFrequency ?? action.gtoFrequency) * 100;

  const handleClick = () => {
    if (onActionClick) {
      onActionClick(action.action);
    }
  };

  return (
    <div
      data-testid={`action-bar-${action.action}`}
      style={{
        display: "flex",
        flexDirection: "column",
        marginBottom: "16px",
        cursor: onActionClick ? "pointer" : "default",
      }}
      onClick={handleClick}
    >
      {/* Action label and EV value */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          marginBottom: "4px",
        }}
      >
        <span
          style={{
            fontWeight: "bold",
            textTransform: "capitalize",
          }}
        >
          {action.action}
        </span>
        <span
          data-testid={`ev-value-${action.action}`}
          style={{
            color: action.ev >= 0 ? "#28a745" : "#dc3545",
            fontWeight: "bold",
          }}
        >
          {formatEV(action.ev)}
        </span>
      </div>

      {/* EV bar */}
      <div
        style={{
          width: `${width}px`,
          height: "24px",
          backgroundColor: "#e9ecef",
          borderRadius: "4px",
          overflow: "hidden",
          marginBottom: "4px",
        }}
      >
        <div
          data-testid={`ev-bar-${action.action}`}
          style={{
            width: `${evBarWidth}%`,
            height: "100%",
            backgroundColor: getBarColor(action.ev, barColor),
            transition: "width 0.3s ease",
          }}
        />
      </div>

      {/* Frequency bars */}
      <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
        {/* GTO frequency bar */}
        <div style={{ flex: 1 }}>
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              fontSize: "12px",
              marginBottom: "2px",
            }}
          >
            <span>GTO</span>
            <span data-testid={`gto-freq-${action.action}`}>
              {formatFrequency(action.gtoFrequency)}
            </span>
          </div>
          <div
            style={{
              width: "100%",
              height: "12px",
              backgroundColor: "#e9ecef",
              borderRadius: "2px",
              overflow: "hidden",
            }}
          >
            <div
              data-testid={`gto-bar-${action.action}`}
              style={{
                width: `${gtoBarWidth}%`,
                height: "100%",
                backgroundColor: barColor,
                opacity: 0.7,
              }}
            />
          </div>
        </div>

        {/* Exploit frequency bar (if enabled and different from GTO) */}
        {showExploit && action.exploitFrequency !== undefined && (
          <div style={{ flex: 1 }}>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                fontSize: "12px",
                marginBottom: "2px",
              }}
            >
              <span>Exploit</span>
              <span data-testid={`exploit-freq-${action.action}`}>
                {formatFrequency(action.exploitFrequency)}
              </span>
            </div>
            <div
              style={{
                width: "100%",
                height: "12px",
                backgroundColor: "#e9ecef",
                borderRadius: "2px",
                overflow: "hidden",
              }}
            >
              <div
                data-testid={`exploit-bar-${action.action}`}
                style={{
                  width: `${exploitBarWidth}%`,
                  height: "100%",
                  backgroundColor: exploitBarColor,
                  opacity: 0.9,
                }}
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

/**
 * EVSummary - Summary statistics for the action comparison
 */
interface EVSummaryProps {
  actions: ActionEV[];
}

const EVSummary: React.FC<EVSummaryProps> = ({ actions }) => {
  if (actions.length === 0) return null;

  // Find best action by EV
  const bestAction = actions.reduce((best, current) =>
    current.ev > best.ev ? current : best
  );

  // Calculate EV difference between best and worst
  const worstAction = actions.reduce((worst, current) =>
    current.ev < worst.ev ? current : worst
  );
  const evSpread = bestAction.ev - worstAction.ev;

  return (
    <div
      data-testid="ev-summary"
      style={{
        padding: "12px",
        backgroundColor: "#f8f9fa",
        borderRadius: "4px",
        marginTop: "16px",
      }}
    >
      <div style={{ marginBottom: "8px" }}>
        <strong>Best Action:</strong>{" "}
        <span
          data-testid="best-action"
          style={{ textTransform: "capitalize", color: "#28a745" }}
        >
          {bestAction.action}
        </span>{" "}
        ({formatEV(bestAction.ev)})
      </div>
      <div>
        <strong>EV Spread:</strong>{" "}
        <span data-testid="ev-spread">{evSpread.toFixed(2)} BB</span>
      </div>
    </div>
  );
};

/**
 * Main EVChart component
 */
export const EVChart: React.FC<EVChartProps> = ({
  actions,
  title = "EV Comparison",
  showExploit = true,
  onActionClick,
  barColor = DEFAULT_BAR_COLOR,
  exploitBarColor = DEFAULT_EXPLOIT_COLOR,
  width = 300,
  height,
}) => {
  // Sort actions by EV (highest first)
  const sortedActions = [...actions].sort((a, b) => b.ev - a.ev);

  // Find max absolute EV for scaling bars
  const maxAbsEV = Math.max(...actions.map((a) => Math.abs(a.ev)), 0.01);

  if (actions.length === 0) {
    return (
      <div data-testid="ev-chart-empty" style={{ padding: "20px" }}>
        No actions to compare
      </div>
    );
  }

  return (
    <div
      data-testid="ev-chart"
      style={{
        width: `${width}px`,
        padding: "16px",
        backgroundColor: "#fff",
        borderRadius: "8px",
        boxShadow: "0 2px 4px rgba(0,0,0,0.1)",
      }}
    >
      {title && (
        <h3
          data-testid="ev-chart-title"
          style={{
            marginTop: 0,
            marginBottom: "16px",
            fontSize: "16px",
            fontWeight: "bold",
          }}
        >
          {title}
        </h3>
      )}

      {sortedActions.map((action) => (
        <ActionBar
          key={action.action}
          action={action}
          maxAbsEV={maxAbsEV}
          showExploit={showExploit}
          barColor={barColor}
          exploitBarColor={exploitBarColor}
          onActionClick={onActionClick}
          width={width - 32}
        />
      ))}

      <EVSummary actions={sortedActions} />
    </div>
  );
};

/**
 * Helper function to create ActionEV data from solver output
 */
export function createActionEVFromSolver(
  solverData: {
    actions: Record<string, number>; // action -> frequency
    ev: Record<string, number>; // action -> EV
  },
  exploitAdjustments?: Record<string, number>
): ActionEV[] {
  const result: ActionEV[] = [];

  for (const [action, frequency] of Object.entries(solverData.actions)) {
    const actionType = action as ActionType;
    result.push({
      action: actionType,
      ev: solverData.ev[action] ?? 0,
      gtoFrequency: frequency,
      exploitFrequency: exploitAdjustments?.[action],
    });
  }

  return result;
}

export default EVChart;
