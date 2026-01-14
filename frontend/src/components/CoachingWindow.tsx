/**
 * CoachingWindow - Main coaching overlay component
 *
 * Displays real-time coaching advice during poker play:
 * - Decision panel with recommended action and frequency
 * - Range visualization (hand matrix)
 * - EV comparison chart for available actions
 * - Exploit suggestions based on opponent profiles
 */

import React, { useState, useEffect } from "react";

// Types for coaching data
interface ActionFrequency {
  action: "fold" | "check" | "call" | "bet" | "raise" | "all-in";
  frequency: number;
  ev?: number;
}

interface CoachingAdvice {
  recommended_action: string;
  action_frequencies: ActionFrequency[];
  ev_comparison: Record<string, number>;
  exploit_suggestions: string[];
  range_display?: string[][];
}

interface GameStateUpdate {
  pot: number;
  effective_stack: number;
  board: string[];
  hero_cards: string[];
  position: string;
  to_call: number;
  street: "preflop" | "flop" | "turn" | "river";
}

interface CoachingWindowProps {
  websocketUrl?: string;
  onClose?: () => void;
}

/**
 * Decision Panel Component
 * Shows recommended action with frequency bars
 */
const DecisionPanel: React.FC<{
  advice: CoachingAdvice | null;
  loading: boolean;
}> = ({ advice, loading }) => {
  if (loading) {
    return (
      <div className="decision-panel loading">
        <div className="spinner" />
        <span>Analyzing...</span>
      </div>
    );
  }

  if (!advice) {
    return (
      <div className="decision-panel empty">
        <span>Waiting for game state...</span>
      </div>
    );
  }

  return (
    <div className="decision-panel">
      <h2>Recommended Action</h2>
      <div className="recommended-action">{advice.recommended_action}</div>

      <div className="action-frequencies">
        {advice.action_frequencies.map(({ action, frequency, ev }) => (
          <div key={action} className="frequency-bar">
            <span className="action-label">{action}</span>
            <div className="bar-container">
              <div
                className="bar-fill"
                style={{ width: `${frequency * 100}%` }}
              />
            </div>
            <span className="frequency-value">{(frequency * 100).toFixed(0)}%</span>
            {ev !== undefined && (
              <span className="ev-value">EV: {ev.toFixed(2)}</span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

/**
 * Range Display Component
 * Shows hand range matrix (13x13 grid)
 */
const RangeDisplay: React.FC<{
  range: string[][] | undefined;
}> = ({ range }) => {
  const ranks = ["A", "K", "Q", "J", "T", "9", "8", "7", "6", "5", "4", "3", "2"];

  if (!range) {
    return (
      <div className="range-display empty">
        <span>Range not available</span>
      </div>
    );
  }

  return (
    <div className="range-display">
      <h3>Range</h3>
      <div className="range-grid">
        {ranks.map((row, i) =>
          ranks.map((col, j) => {
            const hand = i <= j ? `${row}${col}${i === j ? "" : "s"}` : `${col}${row}o`;
            const inRange = range[i]?.[j] === "1";
            return (
              <div
                key={`${i}-${j}`}
                className={`range-cell ${inRange ? "in-range" : "out-range"}`}
                title={hand}
              >
                {i === j ? row + row : i < j ? row + col + "s" : col + row + "o"}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};

/**
 * EV Comparison Chart Component
 * Bar chart comparing EV of different actions
 */
const EVComparisonChart: React.FC<{
  evComparison: Record<string, number> | undefined;
}> = ({ evComparison }) => {
  if (!evComparison || Object.keys(evComparison).length === 0) {
    return (
      <div className="ev-chart empty">
        <span>EV data not available</span>
      </div>
    );
  }

  const maxEV = Math.max(...Object.values(evComparison));
  const minEV = Math.min(...Object.values(evComparison));
  const range = maxEV - minEV || 1;

  return (
    <div className="ev-chart">
      <h3>EV Comparison</h3>
      <div className="ev-bars">
        {Object.entries(evComparison).map(([action, ev]) => (
          <div key={action} className="ev-bar-container">
            <span className="action-name">{action}</span>
            <div className="ev-bar-wrapper">
              <div
                className={`ev-bar ${ev >= 0 ? "positive" : "negative"}`}
                style={{
                  width: `${Math.abs((ev - minEV) / range) * 100}%`,
                }}
              />
            </div>
            <span className="ev-value">{ev.toFixed(2)} BB</span>
          </div>
        ))}
      </div>
    </div>
  );
};

/**
 * Exploit Suggestions Component
 * Shows opponent-specific adjustments
 */
const ExploitSuggestions: React.FC<{
  suggestions: string[];
}> = ({ suggestions }) => {
  if (!suggestions || suggestions.length === 0) {
    return null;
  }

  return (
    <div className="exploit-suggestions">
      <h3>Exploit Opportunities</h3>
      <ul>
        {suggestions.map((suggestion, i) => (
          <li key={i}>{suggestion}</li>
        ))}
      </ul>
    </div>
  );
};

/**
 * Game Info Display
 * Shows current game state
 */
const GameInfo: React.FC<{
  gameState: GameStateUpdate | null;
}> = ({ gameState }) => {
  if (!gameState) {
    return null;
  }

  return (
    <div className="game-info">
      <div className="info-row">
        <span>Position:</span>
        <strong>{gameState.position}</strong>
      </div>
      <div className="info-row">
        <span>Street:</span>
        <strong>{gameState.street}</strong>
      </div>
      <div className="info-row">
        <span>Pot:</span>
        <strong>{gameState.pot} BB</strong>
      </div>
      <div className="info-row">
        <span>To Call:</span>
        <strong>{gameState.to_call} BB</strong>
      </div>
      <div className="info-row">
        <span>Effective Stack:</span>
        <strong>{gameState.effective_stack} BB</strong>
      </div>
      {gameState.hero_cards.length > 0 && (
        <div className="info-row">
          <span>Hand:</span>
          <strong>{gameState.hero_cards.join("")}</strong>
        </div>
      )}
      {gameState.board.length > 0 && (
        <div className="info-row">
          <span>Board:</span>
          <strong>{gameState.board.join(" ")}</strong>
        </div>
      )}
    </div>
  );
};

/**
 * Main CoachingWindow Component
 */
export const CoachingWindow: React.FC<CoachingWindowProps> = ({
  websocketUrl = "ws://localhost:8000/ws/coach",
  onClose,
}) => {
  const [connected, setConnected] = useState(false);
  const [gameState, setGameState] = useState<GameStateUpdate | null>(null);
  const [advice, setAdvice] = useState<CoachingAdvice | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let ws: WebSocket | null = null;
    let reconnectTimeout: NodeJS.Timeout | null = null;

    const connect = () => {
      try {
        ws = new WebSocket(websocketUrl);

        ws.onopen = () => {
          setConnected(true);
          setError(null);
        };

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);

            if (data.type === "game_state") {
              setGameState(data.payload);
              setLoading(true);
            } else if (data.type === "coaching_advice") {
              setAdvice(data.payload);
              setLoading(false);
            } else if (data.type === "error") {
              setError(data.message);
              setLoading(false);
            }
          } catch (e) {
            console.error("Failed to parse WebSocket message:", e);
          }
        };

        ws.onclose = () => {
          setConnected(false);
          // Attempt to reconnect after 3 seconds
          reconnectTimeout = setTimeout(connect, 3000);
        };

        ws.onerror = (err) => {
          console.error("WebSocket error:", err);
          setError("Connection error");
        };
      } catch (e) {
        setError("Failed to connect");
      }
    };

    connect();

    return () => {
      if (ws) {
        ws.close();
      }
      if (reconnectTimeout) {
        clearTimeout(reconnectTimeout);
      }
    };
  }, [websocketUrl]);

  return (
    <div className="coaching-window">
      <header className="coaching-header">
        <h1>PokerCoach</h1>
        <div className="connection-status">
          <span className={`status-dot ${connected ? "connected" : "disconnected"}`} />
          {connected ? "Connected" : "Disconnected"}
        </div>
        {onClose && (
          <button className="close-btn" onClick={onClose}>
            X
          </button>
        )}
      </header>

      {error && <div className="error-banner">{error}</div>}

      <div className="coaching-content">
        <div className="left-panel">
          <GameInfo gameState={gameState} />
          <DecisionPanel advice={advice} loading={loading} />
        </div>

        <div className="right-panel">
          <RangeDisplay range={advice?.range_display} />
          <EVComparisonChart evComparison={advice?.ev_comparison} />
          <ExploitSuggestions suggestions={advice?.exploit_suggestions || []} />
        </div>
      </div>

      <footer className="coaching-footer">
        <span>GTO-based advice | Latency: &lt;500ms target</span>
      </footer>
    </div>
  );
};

export default CoachingWindow;
