/**
 * DecisionTimeline - Scrollable timeline of past decisions
 *
 * Shows a chronological list of decisions made during the session with:
 * - Hand summary (cards, position, action taken)
 * - GTO recommendation vs actual action
 * - EV impact indicator
 * - Click to expand for full solver analysis
 * - Mistake flagging and learning opportunities
 */

import React, { useState, useEffect, useCallback, useRef } from "react";

// Types for decision history
export interface DecisionRecord {
  id: string;
  timestamp: string;
  hand_id: string;
  hero_cards: string[];
  position: string;
  street: "preflop" | "flop" | "turn" | "river";
  board: string[];
  pot_size: number;
  action_taken: string;
  gto_recommendation: string;
  gto_frequency: number;
  ev_difference: number;
  is_mistake: boolean;
  mistake_severity?: "minor" | "moderate" | "major";
  solver_analysis?: SolverAnalysis;
}

export interface SolverAnalysis {
  action_frequencies: Record<string, number>;
  ev_comparison: Record<string, number>;
  explanation: string;
  exploit_notes?: string;
}

export interface DecisionTimelineProps {
  decisions?: DecisionRecord[];
  onDecisionClick?: (decision: DecisionRecord) => void;
  onLoadMore?: () => void;
  loading?: boolean;
  hasMore?: boolean;
}

/**
 * Format timestamp for display
 */
const formatTimestamp = (timestamp: string): string => {
  const date = new Date(timestamp);
  return date.toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
};

/**
 * Get severity color class
 */
const getSeverityClass = (
  isMistake: boolean,
  severity?: "minor" | "moderate" | "major"
): string => {
  if (!isMistake) return "decision-good";
  switch (severity) {
    case "major":
      return "decision-major-mistake";
    case "moderate":
      return "decision-moderate-mistake";
    case "minor":
    default:
      return "decision-minor-mistake";
  }
};

/**
 * Format EV difference for display
 */
const formatEV = (ev: number): string => {
  const sign = ev >= 0 ? "+" : "";
  return `${sign}${ev.toFixed(2)} BB`;
};

/**
 * Individual decision card component
 */
const DecisionCard: React.FC<{
  decision: DecisionRecord;
  isExpanded: boolean;
  onToggle: () => void;
  onAnalyze: () => void;
}> = ({ decision, isExpanded, onToggle, onAnalyze }) => {
  const severityClass = getSeverityClass(
    decision.is_mistake,
    decision.mistake_severity
  );

  return (
    <div className={`decision-card ${severityClass}`} data-testid="decision-card">
      <div
        className="decision-header"
        onClick={onToggle}
        role="button"
        tabIndex={0}
        onKeyPress={(e) => e.key === "Enter" && onToggle()}
        data-testid="decision-header"
      >
        <div className="decision-time">{formatTimestamp(decision.timestamp)}</div>

        <div className="decision-hand">
          <span className="cards">{decision.hero_cards.join("")}</span>
          <span className="position">{decision.position}</span>
          <span className="street">{decision.street}</span>
        </div>

        <div className="decision-action">
          <span className="action-taken">{decision.action_taken}</span>
          {decision.action_taken !== decision.gto_recommendation && (
            <span className="gto-rec">GTO: {decision.gto_recommendation}</span>
          )}
        </div>

        <div className={`decision-ev ${decision.ev_difference >= 0 ? "positive" : "negative"}`}>
          {formatEV(decision.ev_difference)}
        </div>

        <div className="decision-indicators">
          {decision.is_mistake && (
            <span
              className={`mistake-flag ${decision.mistake_severity}`}
              title={`${decision.mistake_severity} mistake`}
              data-testid="mistake-flag"
            >
              !
            </span>
          )}
          <span className={`expand-icon ${isExpanded ? "expanded" : ""}`}>
            {isExpanded ? "v" : ">"}
          </span>
        </div>
      </div>

      {isExpanded && (
        <div className="decision-details" data-testid="decision-details">
          <div className="detail-row">
            <span className="label">Board:</span>
            <span className="value">
              {decision.board.length > 0 ? decision.board.join(" ") : "-"}
            </span>
          </div>

          <div className="detail-row">
            <span className="label">Pot:</span>
            <span className="value">{decision.pot_size} BB</span>
          </div>

          <div className="detail-row">
            <span className="label">GTO Frequency:</span>
            <span className="value">
              {(decision.gto_frequency * 100).toFixed(0)}%
            </span>
          </div>

          {decision.solver_analysis && (
            <div className="solver-analysis">
              <h4>Solver Analysis</h4>

              <div className="frequencies">
                {Object.entries(decision.solver_analysis.action_frequencies).map(
                  ([action, freq]) => (
                    <div key={action} className="freq-bar">
                      <span className="action">{action}</span>
                      <div className="bar-container">
                        <div
                          className="bar-fill"
                          style={{ width: `${freq * 100}%` }}
                        />
                      </div>
                      <span className="freq-value">{(freq * 100).toFixed(0)}%</span>
                    </div>
                  )
                )}
              </div>

              <div className="ev-comparison">
                {Object.entries(decision.solver_analysis.ev_comparison).map(
                  ([action, ev]) => (
                    <div key={action} className="ev-row">
                      <span className="action">{action}</span>
                      <span className={`ev ${ev >= 0 ? "positive" : "negative"}`}>
                        {formatEV(ev)}
                      </span>
                    </div>
                  )
                )}
              </div>

              <p className="explanation">{decision.solver_analysis.explanation}</p>

              {decision.solver_analysis.exploit_notes && (
                <p className="exploit-notes">
                  <strong>Exploit:</strong> {decision.solver_analysis.exploit_notes}
                </p>
              )}
            </div>
          )}

          <button
            className="analyze-btn"
            onClick={onAnalyze}
            data-testid="analyze-button"
          >
            Full Analysis
          </button>
        </div>
      )}
    </div>
  );
};

/**
 * Summary stats component
 */
const TimelineSummary: React.FC<{
  decisions: DecisionRecord[];
}> = ({ decisions }) => {
  const totalDecisions = decisions.length;
  const mistakes = decisions.filter((d) => d.is_mistake);
  const totalEV = decisions.reduce((sum, d) => sum + d.ev_difference, 0);

  const majorMistakes = mistakes.filter((d) => d.mistake_severity === "major").length;
  const moderateMistakes = mistakes.filter((d) => d.mistake_severity === "moderate").length;
  const minorMistakes = mistakes.filter((d) => d.mistake_severity === "minor").length;

  return (
    <div className="timeline-summary" data-testid="timeline-summary">
      <div className="summary-stat">
        <span className="stat-value">{totalDecisions}</span>
        <span className="stat-label">Decisions</span>
      </div>

      <div className="summary-stat">
        <span className={`stat-value ${totalEV >= 0 ? "positive" : "negative"}`}>
          {formatEV(totalEV)}
        </span>
        <span className="stat-label">Total EV</span>
      </div>

      <div className="summary-stat mistakes">
        <div className="mistake-breakdown">
          {majorMistakes > 0 && (
            <span className="major">{majorMistakes} major</span>
          )}
          {moderateMistakes > 0 && (
            <span className="moderate">{moderateMistakes} moderate</span>
          )}
          {minorMistakes > 0 && (
            <span className="minor">{minorMistakes} minor</span>
          )}
          {mistakes.length === 0 && (
            <span className="none">No mistakes!</span>
          )}
        </div>
        <span className="stat-label">Mistakes</span>
      </div>
    </div>
  );
};

/**
 * Filter controls component
 */
const TimelineFilters: React.FC<{
  filter: "all" | "mistakes" | "major";
  onFilterChange: (filter: "all" | "mistakes" | "major") => void;
}> = ({ filter, onFilterChange }) => {
  return (
    <div className="timeline-filters" data-testid="timeline-filters">
      <button
        className={filter === "all" ? "active" : ""}
        onClick={() => onFilterChange("all")}
      >
        All
      </button>
      <button
        className={filter === "mistakes" ? "active" : ""}
        onClick={() => onFilterChange("mistakes")}
      >
        Mistakes
      </button>
      <button
        className={filter === "major" ? "active" : ""}
        onClick={() => onFilterChange("major")}
      >
        Major Only
      </button>
    </div>
  );
};

/**
 * Main DecisionTimeline Component
 */
export const DecisionTimeline: React.FC<DecisionTimelineProps> = ({
  decisions = [],
  onDecisionClick,
  onLoadMore,
  loading = false,
  hasMore = false,
}) => {
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [filter, setFilter] = useState<"all" | "mistakes" | "major">("all");
  const scrollRef = useRef<HTMLDivElement>(null);

  // Filter decisions based on current filter
  const filteredDecisions = decisions.filter((d) => {
    if (filter === "all") return true;
    if (filter === "mistakes") return d.is_mistake;
    if (filter === "major") return d.is_mistake && d.mistake_severity === "major";
    return true;
  });

  // Handle infinite scroll
  const handleScroll = useCallback(() => {
    if (!scrollRef.current || loading || !hasMore) return;

    const { scrollTop, scrollHeight, clientHeight } = scrollRef.current;
    if (scrollHeight - scrollTop - clientHeight < 100) {
      onLoadMore?.();
    }
  }, [loading, hasMore, onLoadMore]);

  useEffect(() => {
    const scrollEl = scrollRef.current;
    if (scrollEl) {
      scrollEl.addEventListener("scroll", handleScroll);
      return () => scrollEl.removeEventListener("scroll", handleScroll);
    }
  }, [handleScroll]);

  const handleToggleExpand = (id: string) => {
    setExpandedId(expandedId === id ? null : id);
  };

  const handleAnalyze = (decision: DecisionRecord) => {
    onDecisionClick?.(decision);
  };

  return (
    <div className="decision-timeline" data-testid="decision-timeline">
      <header className="timeline-header">
        <h2>Decision History</h2>
        <TimelineFilters filter={filter} onFilterChange={setFilter} />
      </header>

      <TimelineSummary decisions={decisions} />

      <div
        className="timeline-scroll"
        ref={scrollRef}
        data-testid="timeline-scroll"
      >
        {filteredDecisions.length === 0 ? (
          <div className="empty-state" data-testid="empty-state">
            {filter === "all"
              ? "No decisions recorded yet"
              : "No matching decisions"}
          </div>
        ) : (
          filteredDecisions.map((decision) => (
            <DecisionCard
              key={decision.id}
              decision={decision}
              isExpanded={expandedId === decision.id}
              onToggle={() => handleToggleExpand(decision.id)}
              onAnalyze={() => handleAnalyze(decision)}
            />
          ))
        )}

        {loading && (
          <div className="loading-indicator" data-testid="loading-indicator">
            Loading more...
          </div>
        )}
      </div>
    </div>
  );
};

export default DecisionTimeline;
