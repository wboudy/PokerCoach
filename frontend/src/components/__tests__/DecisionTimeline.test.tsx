/**
 * Tests for DecisionTimeline component
 */

import React from "react";
import { render, screen, fireEvent, within } from "@testing-library/react";
import "@testing-library/jest-dom";
import { DecisionTimeline, DecisionRecord, SolverAnalysis } from "../DecisionTimeline";

// Mock decision data
const createMockDecision = (overrides: Partial<DecisionRecord> = {}): DecisionRecord => ({
  id: "test-1",
  timestamp: "2026-01-14T12:00:00Z",
  hand_id: "hand-001",
  hero_cards: ["As", "Kh"],
  position: "BTN",
  street: "preflop",
  board: [],
  pot_size: 3.5,
  action_taken: "raise",
  gto_recommendation: "raise",
  gto_frequency: 0.85,
  ev_difference: 0.5,
  is_mistake: false,
  ...overrides,
});

const createMockMistake = (severity: "minor" | "moderate" | "major"): DecisionRecord => ({
  ...createMockDecision(),
  id: `mistake-${severity}`,
  action_taken: "call",
  gto_recommendation: "raise",
  gto_frequency: 0.9,
  ev_difference: -1.5,
  is_mistake: true,
  mistake_severity: severity,
});

describe("DecisionTimeline", () => {
  describe("rendering", () => {
    it("renders empty state when no decisions", () => {
      render(<DecisionTimeline decisions={[]} />);

      expect(screen.getByTestId("empty-state")).toBeInTheDocument();
      expect(screen.getByText("No decisions recorded yet")).toBeInTheDocument();
    });

    it("renders decision cards for each decision", () => {
      const decisions = [
        createMockDecision({ id: "1" }),
        createMockDecision({ id: "2" }),
        createMockDecision({ id: "3" }),
      ];

      render(<DecisionTimeline decisions={decisions} />);

      const cards = screen.getAllByTestId("decision-card");
      expect(cards).toHaveLength(3);
    });

    it("renders timeline summary with correct stats", () => {
      const decisions = [
        createMockDecision({ ev_difference: 1.0 }),
        createMockDecision({ id: "2", ev_difference: -0.5 }),
        createMockMistake("minor"),
      ];

      render(<DecisionTimeline decisions={decisions} />);

      const summary = screen.getByTestId("timeline-summary");
      expect(summary).toBeInTheDocument();

      // Check decision count
      expect(screen.getByText("3")).toBeInTheDocument();
      expect(screen.getByText("Decisions")).toBeInTheDocument();
    });

    it("displays hero cards and position", () => {
      const decisions = [
        createMockDecision({
          hero_cards: ["Qs", "Qh"],
          position: "CO",
        }),
      ];

      render(<DecisionTimeline decisions={decisions} />);

      expect(screen.getByText("QsQh")).toBeInTheDocument();
      expect(screen.getByText("CO")).toBeInTheDocument();
    });
  });

  describe("mistake flagging", () => {
    it("shows mistake flag for mistake decisions", () => {
      const decisions = [createMockMistake("major")];

      render(<DecisionTimeline decisions={decisions} />);

      expect(screen.getByTestId("mistake-flag")).toBeInTheDocument();
    });

    it("does not show mistake flag for correct decisions", () => {
      const decisions = [createMockDecision({ is_mistake: false })];

      render(<DecisionTimeline decisions={decisions} />);

      expect(screen.queryByTestId("mistake-flag")).not.toBeInTheDocument();
    });

    it("applies correct severity class", () => {
      const decisions = [createMockMistake("major")];

      render(<DecisionTimeline decisions={decisions} />);

      const card = screen.getByTestId("decision-card");
      expect(card).toHaveClass("decision-major-mistake");
    });

    it("shows GTO recommendation when different from action taken", () => {
      const decisions = [
        createMockDecision({
          action_taken: "call",
          gto_recommendation: "raise",
        }),
      ];

      render(<DecisionTimeline decisions={decisions} />);

      expect(screen.getByText("GTO: raise")).toBeInTheDocument();
    });
  });

  describe("filtering", () => {
    it("shows all decisions by default", () => {
      const decisions = [
        createMockDecision({ id: "1" }),
        createMockMistake("minor"),
        createMockMistake("major"),
      ];

      render(<DecisionTimeline decisions={decisions} />);

      expect(screen.getAllByTestId("decision-card")).toHaveLength(3);
    });

    it("filters to show only mistakes when filter selected", () => {
      const decisions = [
        createMockDecision({ id: "1" }),
        createMockMistake("minor"),
        createMockMistake("major"),
      ];

      render(<DecisionTimeline decisions={decisions} />);

      // Click mistakes filter
      const filters = screen.getByTestId("timeline-filters");
      fireEvent.click(within(filters).getByText("Mistakes"));

      expect(screen.getAllByTestId("decision-card")).toHaveLength(2);
    });

    it("filters to show only major mistakes", () => {
      const decisions = [
        createMockDecision({ id: "1" }),
        createMockMistake("minor"),
        createMockMistake("major"),
      ];

      render(<DecisionTimeline decisions={decisions} />);

      // Click major only filter
      const filters = screen.getByTestId("timeline-filters");
      fireEvent.click(within(filters).getByText("Major Only"));

      expect(screen.getAllByTestId("decision-card")).toHaveLength(1);
    });

    it("shows empty message when filter has no matches", () => {
      const decisions = [createMockDecision({ id: "1", is_mistake: false })];

      render(<DecisionTimeline decisions={decisions} />);

      // Filter to mistakes (none exist)
      const filters = screen.getByTestId("timeline-filters");
      fireEvent.click(within(filters).getByText("Mistakes"));

      expect(screen.getByText("No matching decisions")).toBeInTheDocument();
    });
  });

  describe("expansion and details", () => {
    it("expands decision on click", () => {
      const decisions = [createMockDecision()];

      render(<DecisionTimeline decisions={decisions} />);

      // Initially not expanded
      expect(screen.queryByTestId("decision-details")).not.toBeInTheDocument();

      // Click to expand
      fireEvent.click(screen.getByTestId("decision-header"));

      // Should now be expanded
      expect(screen.getByTestId("decision-details")).toBeInTheDocument();
    });

    it("collapses decision on second click", () => {
      const decisions = [createMockDecision()];

      render(<DecisionTimeline decisions={decisions} />);

      // Click to expand
      fireEvent.click(screen.getByTestId("decision-header"));
      expect(screen.getByTestId("decision-details")).toBeInTheDocument();

      // Click again to collapse
      fireEvent.click(screen.getByTestId("decision-header"));
      expect(screen.queryByTestId("decision-details")).not.toBeInTheDocument();
    });

    it("shows board cards when expanded", () => {
      const decisions = [
        createMockDecision({
          board: ["Ks", "Qh", "7d"],
          street: "flop",
        }),
      ];

      render(<DecisionTimeline decisions={decisions} />);

      fireEvent.click(screen.getByTestId("decision-header"));

      expect(screen.getByText("Ks Qh 7d")).toBeInTheDocument();
    });

    it("shows solver analysis when available", () => {
      const solverAnalysis: SolverAnalysis = {
        action_frequencies: {
          raise: 0.85,
          call: 0.1,
          fold: 0.05,
        },
        ev_comparison: {
          raise: 2.5,
          call: 1.0,
          fold: 0.0,
        },
        explanation: "Strong hand should raise for value",
      };

      const decisions = [
        createMockDecision({
          solver_analysis: solverAnalysis,
        }),
      ];

      render(<DecisionTimeline decisions={decisions} />);

      fireEvent.click(screen.getByTestId("decision-header"));

      expect(screen.getByText("Solver Analysis")).toBeInTheDocument();
      expect(screen.getByText("Strong hand should raise for value")).toBeInTheDocument();
    });
  });

  describe("callbacks", () => {
    it("calls onDecisionClick when analyze button clicked", () => {
      const onDecisionClick = jest.fn();
      const decision = createMockDecision();
      const decisions = [decision];

      render(
        <DecisionTimeline
          decisions={decisions}
          onDecisionClick={onDecisionClick}
        />
      );

      // Expand first
      fireEvent.click(screen.getByTestId("decision-header"));

      // Click analyze button
      fireEvent.click(screen.getByTestId("analyze-button"));

      expect(onDecisionClick).toHaveBeenCalledWith(decision);
    });
  });

  describe("loading state", () => {
    it("shows loading indicator when loading", () => {
      render(
        <DecisionTimeline
          decisions={[createMockDecision()]}
          loading={true}
          hasMore={true}
        />
      );

      expect(screen.getByTestId("loading-indicator")).toBeInTheDocument();
    });

    it("hides loading indicator when not loading", () => {
      render(
        <DecisionTimeline
          decisions={[createMockDecision()]}
          loading={false}
          hasMore={true}
        />
      );

      expect(screen.queryByTestId("loading-indicator")).not.toBeInTheDocument();
    });
  });

  describe("EV display", () => {
    it("displays positive EV with plus sign", () => {
      const decisions = [createMockDecision({ ev_difference: 1.5 })];

      render(<DecisionTimeline decisions={decisions} />);

      expect(screen.getByText("+1.50 BB")).toBeInTheDocument();
    });

    it("displays negative EV with minus sign", () => {
      const decisions = [createMockDecision({ ev_difference: -2.0 })];

      render(<DecisionTimeline decisions={decisions} />);

      expect(screen.getByText("-2.00 BB")).toBeInTheDocument();
    });

    it("applies positive class for positive EV", () => {
      const decisions = [createMockDecision({ ev_difference: 1.0 })];

      render(<DecisionTimeline decisions={decisions} />);

      const evElement = screen.getByText("+1.00 BB");
      expect(evElement).toHaveClass("positive");
    });

    it("applies negative class for negative EV", () => {
      const decisions = [createMockDecision({ ev_difference: -1.0 })];

      render(<DecisionTimeline decisions={decisions} />);

      const evElement = screen.getByText("-1.00 BB");
      expect(evElement).toHaveClass("negative");
    });
  });
});
