"""Tests for TexasSolver integration."""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from pokercoach.core.game_state import Board, Card, GameState, Street
from pokercoach.solver.texas_solver import (
    DEFAULT_IP_RANGE,
    DEFAULT_OOP_RANGE,
    TexasSolverBridge,
    TexasSolverConfig,
)


@pytest.fixture
def mock_binary_path(tmp_path: Path) -> Path:
    """Create a mock binary file for testing."""
    binary = tmp_path / "texas_solver"
    binary.touch()
    return binary


@pytest.fixture
def solver_config(mock_binary_path: Path) -> TexasSolverConfig:
    """Create a test solver configuration."""
    return TexasSolverConfig(
        binary_path=mock_binary_path,
        threads=4,
        accuracy=0.5,
        max_iterations=500,
        use_isomorphism=True,
        bet_sizes={"flop": [33, 50], "turn": [50, 75], "river": [50, 100]},
    )


@pytest.fixture
def solver_bridge(solver_config: TexasSolverConfig) -> TexasSolverBridge:
    """Create a test solver bridge."""
    return TexasSolverBridge(solver_config)


class TestBuildCommand:
    """Tests for TexasSolverBridge._build_command() method."""

    def test_build_command_returns_list(self, solver_bridge: TexasSolverBridge):
        """Test that _build_command returns a list of strings."""
        game_state = GameState()
        game_state.pot = 50.0
        game_state.effective_stack = 200.0

        # Add flop cards
        for card_str in ["Qs", "Jh", "2h"]:
            game_state.board.add_card(Card.from_string(card_str))

        cmd = solver_bridge._build_command(game_state)

        assert isinstance(cmd, list)
        assert all(isinstance(arg, str) for arg in cmd)

    def test_build_command_starts_with_binary(self, solver_bridge: TexasSolverBridge):
        """Test that command starts with binary path."""
        game_state = GameState()
        game_state.pot = 50.0
        game_state.effective_stack = 200.0

        for card_str in ["Qs", "Jh", "2h"]:
            game_state.board.add_card(Card.from_string(card_str))

        cmd = solver_bridge._build_command(game_state)

        assert cmd[0] == str(solver_bridge.config.binary_path)

    def test_build_command_includes_input_file(self, solver_bridge: TexasSolverBridge):
        """Test that command includes --input_file argument."""
        game_state = GameState()
        game_state.pot = 50.0
        game_state.effective_stack = 200.0

        for card_str in ["Qs", "Jh", "2h"]:
            game_state.board.add_card(Card.from_string(card_str))

        cmd = solver_bridge._build_command(game_state)

        assert "--input_file" in cmd
        input_file_idx = cmd.index("--input_file")
        input_file_path = cmd[input_file_idx + 1]
        assert os.path.exists(input_file_path)

    def test_build_command_creates_temp_file(self, solver_bridge: TexasSolverBridge):
        """Test that a temporary input file is created with correct content."""
        game_state = GameState()
        game_state.pot = 50.0
        game_state.effective_stack = 200.0

        for card_str in ["Qs", "Jh", "2h"]:
            game_state.board.add_card(Card.from_string(card_str))

        cmd = solver_bridge._build_command(game_state)

        input_file_idx = cmd.index("--input_file")
        input_file_path = cmd[input_file_idx + 1]

        with open(input_file_path) as f:
            content = f.read()

        assert "set_pot 50" in content
        assert "set_effective_stack 200" in content
        assert "set_board Qs,Jh,2h" in content

    def test_build_command_includes_resource_dir_when_exists(
        self, mock_binary_path: Path
    ):
        """Test that resource_dir is included when it exists."""
        # Create resource dir next to mock binary
        resource_dir = mock_binary_path.parent / "resources"
        resource_dir.mkdir()

        config = TexasSolverConfig(binary_path=mock_binary_path)
        bridge = TexasSolverBridge(config)

        game_state = GameState()
        game_state.pot = 50.0
        game_state.effective_stack = 200.0

        for card_str in ["Qs", "Jh", "2h"]:
            game_state.board.add_card(Card.from_string(card_str))

        cmd = bridge._build_command(game_state)

        assert "--resource_dir" in cmd
        resource_dir_idx = cmd.index("--resource_dir")
        assert cmd[resource_dir_idx + 1] == str(resource_dir)

    def test_build_command_uses_explicit_resource_dir(self, mock_binary_path: Path):
        """Test that explicit resource_dir config is used."""
        resource_dir = Path("/custom/resources")

        config = TexasSolverConfig(
            binary_path=mock_binary_path, resource_dir=resource_dir
        )
        bridge = TexasSolverBridge(config)

        game_state = GameState()
        game_state.pot = 50.0
        game_state.effective_stack = 200.0

        for card_str in ["Qs", "Jh", "2h"]:
            game_state.board.add_card(Card.from_string(card_str))

        cmd = bridge._build_command(game_state)

        assert "--resource_dir" in cmd
        resource_dir_idx = cmd.index("--resource_dir")
        assert cmd[resource_dir_idx + 1] == str(resource_dir)


class TestGenerateInputFile:
    """Tests for TexasSolverBridge._generate_input_file() method."""

    def test_generate_input_file_includes_pot(self, solver_bridge: TexasSolverBridge):
        """Test that input file includes pot size."""
        game_state = GameState()
        game_state.pot = 100.0
        game_state.effective_stack = 200.0

        content = solver_bridge._generate_input_file(game_state)

        assert "set_pot 100" in content

    def test_generate_input_file_includes_effective_stack(
        self, solver_bridge: TexasSolverBridge
    ):
        """Test that input file includes effective stack."""
        game_state = GameState()
        game_state.pot = 50.0
        game_state.effective_stack = 350.0

        content = solver_bridge._generate_input_file(game_state)

        assert "set_effective_stack 350" in content

    def test_generate_input_file_includes_board_flop(
        self, solver_bridge: TexasSolverBridge
    ):
        """Test that input file includes board cards for flop."""
        game_state = GameState()
        game_state.pot = 50.0
        game_state.effective_stack = 200.0

        for card_str in ["As", "Kd", "Qh"]:
            game_state.board.add_card(Card.from_string(card_str))

        content = solver_bridge._generate_input_file(game_state)

        assert "set_board As,Kd,Qh" in content

    def test_generate_input_file_includes_board_turn(
        self, solver_bridge: TexasSolverBridge
    ):
        """Test that input file includes board cards for turn."""
        game_state = GameState()
        game_state.pot = 50.0
        game_state.effective_stack = 200.0

        for card_str in ["As", "Kd", "Qh", "Jc"]:
            game_state.board.add_card(Card.from_string(card_str))

        content = solver_bridge._generate_input_file(game_state)

        assert "set_board As,Kd,Qh,Jc" in content

    def test_generate_input_file_includes_board_river(
        self, solver_bridge: TexasSolverBridge
    ):
        """Test that input file includes board cards for river."""
        game_state = GameState()
        game_state.pot = 50.0
        game_state.effective_stack = 200.0

        for card_str in ["As", "Kd", "Qh", "Jc", "Ts"]:
            game_state.board.add_card(Card.from_string(card_str))

        content = solver_bridge._generate_input_file(game_state)

        assert "set_board As,Kd,Qh,Jc,Ts" in content

    def test_generate_input_file_no_board_preflop(
        self, solver_bridge: TexasSolverBridge
    ):
        """Test that preflop state has no board line."""
        game_state = GameState()
        game_state.pot = 3.0
        game_state.effective_stack = 100.0

        content = solver_bridge._generate_input_file(game_state)

        assert "set_board" not in content

    def test_generate_input_file_includes_ranges(
        self, solver_bridge: TexasSolverBridge
    ):
        """Test that input file includes both IP and OOP ranges."""
        game_state = GameState()
        game_state.pot = 50.0
        game_state.effective_stack = 200.0

        content = solver_bridge._generate_input_file(game_state)

        assert "set_range_ip" in content
        assert "set_range_oop" in content

    def test_generate_input_file_includes_bet_sizes(
        self, solver_bridge: TexasSolverBridge
    ):
        """Test that input file includes bet sizes from config."""
        game_state = GameState()
        game_state.pot = 50.0
        game_state.effective_stack = 200.0

        content = solver_bridge._generate_input_file(game_state)

        # Check flop bet sizes (33, 50 from config)
        assert "set_bet_sizes oop,flop,bet,33" in content
        assert "set_bet_sizes oop,flop,bet,50" in content
        assert "set_bet_sizes ip,flop,bet,33" in content
        assert "set_bet_sizes ip,flop,bet,50" in content

        # Check turn bet sizes (50, 75 from config)
        assert "set_bet_sizes oop,turn,bet,50" in content
        assert "set_bet_sizes oop,turn,bet,75" in content

        # Check river bet sizes (50, 100 from config)
        assert "set_bet_sizes oop,river,bet,50" in content
        assert "set_bet_sizes oop,river,bet,100" in content

    def test_generate_input_file_includes_raise_sizes(
        self, solver_bridge: TexasSolverBridge
    ):
        """Test that input file includes raise sizes."""
        game_state = GameState()
        game_state.pot = 50.0
        game_state.effective_stack = 200.0

        content = solver_bridge._generate_input_file(game_state)

        assert "set_bet_sizes oop,flop,raise,33" in content
        assert "set_bet_sizes ip,flop,raise,50" in content

    def test_generate_input_file_includes_allin(
        self, solver_bridge: TexasSolverBridge
    ):
        """Test that input file includes allin options."""
        game_state = GameState()
        game_state.pot = 50.0
        game_state.effective_stack = 200.0

        content = solver_bridge._generate_input_file(game_state)

        assert "set_bet_sizes oop,flop,allin" in content
        assert "set_bet_sizes ip,flop,allin" in content
        assert "set_bet_sizes oop,turn,allin" in content
        assert "set_bet_sizes ip,turn,allin" in content
        assert "set_bet_sizes oop,river,allin" in content
        assert "set_bet_sizes ip,river,allin" in content

    def test_generate_input_file_includes_allin_threshold(
        self, solver_bridge: TexasSolverBridge
    ):
        """Test that input file includes allin threshold."""
        game_state = GameState()
        game_state.pot = 50.0
        game_state.effective_stack = 200.0

        content = solver_bridge._generate_input_file(game_state)

        assert "set_allin_threshold 0.67" in content

    def test_generate_input_file_includes_build_tree(
        self, solver_bridge: TexasSolverBridge
    ):
        """Test that input file includes build_tree command."""
        game_state = GameState()
        game_state.pot = 50.0
        game_state.effective_stack = 200.0

        content = solver_bridge._generate_input_file(game_state)

        assert "build_tree" in content

    def test_generate_input_file_includes_solver_config(
        self, solver_bridge: TexasSolverBridge
    ):
        """Test that input file includes solver configuration."""
        game_state = GameState()
        game_state.pot = 50.0
        game_state.effective_stack = 200.0

        content = solver_bridge._generate_input_file(game_state)

        # Check values from solver_config fixture
        assert "set_thread_num 4" in content
        assert "set_accuracy 0.5" in content
        assert "set_max_iteration 500" in content
        assert "set_use_isomorphism 1" in content

    def test_generate_input_file_includes_start_solve(
        self, solver_bridge: TexasSolverBridge
    ):
        """Test that input file includes start_solve command."""
        game_state = GameState()
        game_state.pot = 50.0
        game_state.effective_stack = 200.0

        content = solver_bridge._generate_input_file(game_state)

        assert "start_solve" in content

    def test_generate_input_file_includes_dump_result(
        self, solver_bridge: TexasSolverBridge
    ):
        """Test that input file includes dump_result command."""
        game_state = GameState()
        game_state.pot = 50.0
        game_state.effective_stack = 200.0

        content = solver_bridge._generate_input_file(game_state)

        assert "dump_result output_result.json" in content

    def test_generate_input_file_command_order(
        self, solver_bridge: TexasSolverBridge
    ):
        """Test that commands are in correct order."""
        game_state = GameState()
        game_state.pot = 50.0
        game_state.effective_stack = 200.0

        for card_str in ["As", "Kd", "Qh"]:
            game_state.board.add_card(Card.from_string(card_str))

        content = solver_bridge._generate_input_file(game_state)
        lines = content.split("\n")

        # Find indices of key commands
        pot_idx = next(i for i, line in enumerate(lines) if "set_pot" in line)
        build_tree_idx = next(i for i, line in enumerate(lines) if line == "build_tree")
        start_solve_idx = next(
            i for i, line in enumerate(lines) if line == "start_solve"
        )
        dump_idx = next(i for i, line in enumerate(lines) if "dump_result" in line)

        # Verify order: pot/stack/board -> bet sizes -> build_tree -> config -> start_solve -> dump
        assert pot_idx < build_tree_idx
        assert build_tree_idx < start_solve_idx
        assert start_solve_idx < dump_idx


class TestTexasSolverConfig:
    """Tests for TexasSolverConfig dataclass."""

    def test_default_config(self, mock_binary_path: Path):
        """Test default configuration values."""
        config = TexasSolverConfig(binary_path=mock_binary_path)

        assert config.threads == 6
        assert config.accuracy == 0.3
        assert config.max_iterations == 1000
        assert config.use_isomorphism is True
        assert config.allin_threshold == 0.67
        assert config.dump_rounds == 2

    def test_config_with_custom_values(self, mock_binary_path: Path):
        """Test configuration with custom values."""
        config = TexasSolverConfig(
            binary_path=mock_binary_path,
            threads=12,
            accuracy=0.1,
            max_iterations=5000,
            use_isomorphism=False,
            bet_sizes={"flop": [25, 75], "turn": [100]},
        )

        assert config.threads == 12
        assert config.accuracy == 0.1
        assert config.max_iterations == 5000
        assert config.use_isomorphism is False
        assert config.bet_sizes == {"flop": [25, 75], "turn": [100]}

    def test_default_ranges(self, mock_binary_path: Path):
        """Test that default ranges are set."""
        config = TexasSolverConfig(binary_path=mock_binary_path)

        assert config.ip_range == DEFAULT_IP_RANGE
        assert config.oop_range == DEFAULT_OOP_RANGE


class TestTexasSolverBridge:
    """Tests for TexasSolverBridge class."""

    def test_init_validates_binary(self, tmp_path: Path):
        """Test that init validates binary exists."""
        non_existent = tmp_path / "non_existent_solver"
        config = TexasSolverConfig(binary_path=non_existent)

        with pytest.raises(FileNotFoundError) as exc_info:
            TexasSolverBridge(config)

        assert "TexasSolver binary not found" in str(exc_info.value)

    def test_init_with_valid_binary(self, mock_binary_path: Path):
        """Test that init succeeds with valid binary."""
        config = TexasSolverConfig(binary_path=mock_binary_path)
        bridge = TexasSolverBridge(config)

        assert bridge.config == config
