"""Main LLM coach interface with tool access."""

from dataclasses import dataclass
from typing import Any, Optional

from pokercoach.core.game_state import GameState, Hand
from pokercoach.solver.bridge import SolverBridge


@dataclass
class CoachConfig:
    """Configuration for the poker coach."""

    model: str = "claude-sonnet-4-20250514"
    api_key: Optional[str] = None
    temperature: float = 0.3
    max_tokens: int = 2048


class PokerCoach:
    """
    AI poker coach that combines LLM reasoning with solver tools.

    The coach can:
    - Query GTO strategy for any position
    - Explain strategic reasoning in natural language
    - Compare action EVs
    - Identify leaks in player's game
    """

    def __init__(self, config: CoachConfig, solver: SolverBridge):
        self.config = config
        self.solver = solver
        self._client: Any = None

    def _get_client(self) -> Any:
        """Lazy initialization of LLM client."""
        if self._client is None:
            import anthropic

            self._client = anthropic.Anthropic(api_key=self.config.api_key)
        return self._client

    def _build_tools(self) -> list[dict[str, Any]]:
        """Build tool definitions for LLM."""
        return [
            {
                "name": "query_gto",
                "description": "Query GTO solver for optimal strategy in a poker spot",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "hand": {
                            "type": "string",
                            "description": "Hero's hand in format like 'AsKs' or 'JhTd'",
                        },
                        "board": {
                            "type": "string",
                            "description": "Board cards like 'Ah Kd 2c' or empty for preflop",
                        },
                        "pot_size": {
                            "type": "number",
                            "description": "Current pot size in big blinds",
                        },
                        "to_call": {
                            "type": "number",
                            "description": "Amount to call in big blinds (0 if checking)",
                        },
                        "effective_stack": {
                            "type": "number",
                            "description": "Effective stack in big blinds",
                        },
                        "position": {
                            "type": "string",
                            "description": "Hero's position (BTN, CO, HJ, MP, UTG, BB, SB)",
                        },
                    },
                    "required": ["hand", "position"],
                },
            },
            {
                "name": "compare_actions",
                "description": "Compare expected values of different actions",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "hand": {"type": "string", "description": "Hero's hand"},
                        "actions": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Actions to compare like ['fold', 'call', 'raise 3x']",
                        },
                    },
                    "required": ["hand", "actions"],
                },
            },
            {
                "name": "explain_line",
                "description": "Explain the strategic reasoning behind a line of play",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "hand": {"type": "string", "description": "Hero's hand"},
                        "line": {
                            "type": "string",
                            "description": "The line taken, e.g., 'call preflop, check-call flop'",
                        },
                    },
                    "required": ["hand", "line"],
                },
            },
        ]

    def _handle_tool_call(self, tool_name: str, tool_input: dict[str, Any]) -> str:
        """Execute a tool call and return result."""
        if tool_name == "query_gto":
            return self._query_gto(**tool_input)
        elif tool_name == "compare_actions":
            return self._compare_actions(**tool_input)
        elif tool_name == "explain_line":
            return self._explain_line(**tool_input)
        else:
            return f"Unknown tool: {tool_name}"

    def _query_gto(
        self,
        hand: str,
        position: str,
        board: str = "",
        pot_size: float = 0,
        to_call: float = 0,
        effective_stack: float = 100,
    ) -> str:
        """Query solver for GTO strategy."""
        # TODO: Build game state and query solver
        # For now, return placeholder
        return f"GTO strategy for {hand} from {position}: [Not yet implemented]"

    def _compare_actions(self, hand: str, actions: list[str]) -> str:
        """Compare EVs of different actions."""
        # TODO: Implement via solver
        return f"Action comparison for {hand}: [Not yet implemented]"

    def _explain_line(self, hand: str, line: str) -> str:
        """Explain strategic reasoning."""
        # TODO: Query solver and generate explanation
        return f"Explanation for {hand} playing {line}: [Not yet implemented]"

    def ask(self, question: str, game_state: Optional[GameState] = None) -> str:
        """
        Ask the coach a poker question.

        Args:
            question: Natural language question about poker strategy
            game_state: Optional current game state for context

        Returns:
            Coach's response with strategic advice
        """
        client = self._get_client()

        system_prompt = """You are an expert poker coach with deep knowledge of GTO
(Game Theory Optimal) strategy and exploitative play. You have access to a GTO solver
to provide mathematically optimal advice.

When answering questions:
1. Use the query_gto tool to get precise strategy recommendations
2. Explain the strategic reasoning in accessible terms
3. Consider both GTO play and exploitative adjustments when relevant
4. Be specific about frequencies and sizing when applicable

Always ground your advice in solver-backed analysis."""

        messages = [{"role": "user", "content": question}]

        if game_state:
            context = f"\nCurrent game state:\n{game_state}"
            messages[0]["content"] = question + context

        response = client.messages.create(
            model=self.config.model,
            max_tokens=self.config.max_tokens,
            system=system_prompt,
            tools=self._build_tools(),
            messages=messages,
        )

        # Handle tool use in response
        while response.stop_reason == "tool_use":
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result = self._handle_tool_call(block.name, block.input)
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result,
                        }
                    )

            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})

            response = client.messages.create(
                model=self.config.model,
                max_tokens=self.config.max_tokens,
                system=system_prompt,
                tools=self._build_tools(),
                messages=messages,
            )

        # Extract text response
        for block in response.content:
            if hasattr(block, "text"):
                return block.text

        return "Unable to generate response"
