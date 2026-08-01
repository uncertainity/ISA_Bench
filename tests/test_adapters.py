"""Tests for game adapters."""

import pytest

from isa_bench.openenv.adapters import get_adapter, ADAPTERS
from isa_bench.openenv.adapters.base import ExecutionResult
from isa_bench.openenv.adapters.hrm import HRMAdapter


class TestHRMAdapter:
    """Tests for HRM adapter."""

    @pytest.fixture
    def adapter(self):
        return HRMAdapter()

    def test_game_name(self, adapter):
        assert adapter.game_name == "hrm"

    def test_metric_names(self, adapter):
        assert "steps" in adapter.metric_names
        assert "instructions" in adapter.metric_names

    def test_load_puzzles(self, adapter):
        puzzles = adapter.load_puzzles()
        assert len(puzzles) > 0
        # Should exclude cutscenes
        for p in puzzles:
            assert not p.is_cutscene

    def test_get_puzzle_by_number(self, adapter):
        puzzle = adapter.get_puzzle("1")
        assert puzzle.number == 1
        assert puzzle.name == "Mail Room"

    def test_get_puzzle_by_id(self, adapter):
        puzzle = adapter.get_puzzle("hrm_level_1")
        assert puzzle.number == 1

    def test_get_puzzle_id(self, adapter):
        puzzle = adapter.get_puzzle("1")
        assert adapter.get_puzzle_id(puzzle) == "hrm_level_1"

    def test_get_puzzle_name(self, adapter):
        puzzle = adapter.get_puzzle("1")
        assert adapter.get_puzzle_name(puzzle) == "Mail Room"

    def test_get_commands(self, adapter):
        puzzle = adapter.get_puzzle("1")
        commands = adapter.get_commands(puzzle)
        assert isinstance(commands, list)
        assert len(commands) > 0

    def test_format_description(self, adapter):
        puzzle = adapter.get_puzzle("1")
        desc = adapter.format_description(puzzle)
        assert isinstance(desc, str)
        assert len(desc) > 0

    def test_execute_correct_solution(self, adapter):
        """Test executing a correct solution for Mail Room."""
        puzzle = adapter.get_puzzle("1")
        code = """
a:
    INBOX
    OUTBOX
    JUMP a
"""
        result = adapter.execute(code, puzzle)

        assert isinstance(result, ExecutionResult)
        assert result.success
        assert result.tests_passed == result.tests_total
        assert result.parse_error is None
        assert result.runtime_error is None
        assert "steps" in result.metrics
        assert "instructions" in result.metrics

    def test_execute_wrong_solution(self, adapter):
        """Test executing an incorrect solution."""
        puzzle = adapter.get_puzzle("1")
        code = "INBOX"  # Just inbox, no outbox

        result = adapter.execute(code, puzzle)

        assert not result.success
        assert result.tests_passed < result.tests_total

    def test_execute_parse_error(self, adapter):
        """Test handling of parse errors."""
        puzzle = adapter.get_puzzle("1")
        code = "INVALID_INSTRUCTION"

        result = adapter.execute(code, puzzle)

        assert not result.success
        assert result.parse_error is not None

    def test_execute_runtime_error(self, adapter):
        """Test handling of runtime errors."""
        puzzle = adapter.get_puzzle("1")
        code = "OUTBOX"  # Empty hands error

        result = adapter.execute(code, puzzle)

        assert not result.success
        # Either parse error or runtime error
        assert (
            result.runtime_error is not None or result.tests_passed < result.tests_total
        )

    def test_get_par(self, adapter):
        """Test par value retrieval."""
        # Level 2 has challenges
        puzzle = adapter.get_puzzle("2")
        par = adapter.get_par(puzzle)

        if par is not None:
            assert "instructions" in par or "steps" in par


class TestSIC1Adapter:
    """Tests for SIC-1 adapter."""

    @pytest.fixture
    def adapter(self):
        from isa_bench.openenv.adapters.sic1 import SIC1Adapter

        return SIC1Adapter()

    def test_game_name(self, adapter):
        assert adapter.game_name == "sic1"

    def test_load_puzzles(self, adapter):
        puzzles = adapter.load_puzzles()
        assert len(puzzles) > 0

    def test_execute_simple_program(self, adapter):
        """Test execution runs without error."""
        puzzles = adapter.load_puzzles()
        puzzle = puzzles[0]  # First puzzle
        # Simple program that might not solve but tests execution
        code = "subleq @OUT, @IN"
        result = adapter.execute(code, puzzle)
        assert isinstance(result, ExecutionResult)


class TestTIS100Adapter:
    """Tests for TIS-100 adapter."""

    @pytest.fixture
    def adapter(self):
        from isa_bench.openenv.adapters.tis100 import TIS100Adapter

        return TIS100Adapter()

    def test_game_name(self, adapter):
        assert adapter.game_name == "tis100"

    def test_load_puzzles(self, adapter):
        puzzles = adapter.load_puzzles()
        assert len(puzzles) > 0

    def test_execute_signal_amplifier(self, adapter):
        """Test signal amplifier execution."""
        puzzle = adapter.get_puzzle("signal_amplifier")
        code = """
@0
MOV UP, ACC
ADD ACC
MOV ACC, DOWN
@4
MOV UP, DOWN
"""
        result = adapter.execute(code, puzzle)
        assert isinstance(result, ExecutionResult)
        # Just verify execution runs - the solution may not be fully correct
        assert result.tests_total > 0


class TestBOX256Adapter:
    """Tests for BOX-256 adapter."""

    @pytest.fixture
    def adapter(self):
        from isa_bench.openenv.adapters.box256 import BOX256Adapter

        return BOX256Adapter()

    def test_game_name(self, adapter):
        assert adapter.game_name == "box256"

    def test_load_puzzles(self, adapter):
        puzzles = adapter.load_puzzles()
        assert len(puzzles) > 0

    def test_execute_simple_program(self, adapter):
        """Test a simple pixel-setting program."""
        puzzle = adapter.get_puzzle(1)  # Rectangle frame
        # This won't solve the puzzle but tests execution
        code = "MOV #1 @80"
        result = adapter.execute(code, puzzle)
        assert isinstance(result, ExecutionResult)
        assert "pixel_accuracy" in result.metrics


class TestMHRDAdapter:
    """Tests for MHRD adapter."""

    @pytest.fixture
    def adapter(self):
        from isa_bench.openenv.adapters.mhrd import MHRDAdapter

        return MHRDAdapter()

    def test_game_name(self, adapter):
        assert adapter.game_name == "mhrd"

    def test_load_puzzles(self, adapter):
        puzzles = adapter.load_puzzles()
        assert len(puzzles) == 8  # NOT, AND, OR, XOR, MUX, DEMUX, HALFADDER, FULLADDER

    def test_execute_not_gate(self, adapter):
        """Test NOT gate solution."""
        puzzle = adapter.get_puzzle("NOT")
        code = """
Inputs: in;
Outputs: out;
Parts: n NAND;
Wires: in -> n.in1, in -> n.in2, n.out -> out;
"""
        result = adapter.execute(code, puzzle)
        assert isinstance(result, ExecutionResult)
        assert result.success
        assert result.metrics["nand_count"] == 1


class TestGetAdapter:
    """Tests for adapter factory."""

    def test_get_hrm_adapter(self):
        adapter = get_adapter("hrm")
        assert isinstance(adapter, HRMAdapter)

    def test_get_all_adapters(self):
        for game in ["hrm", "sic1", "tis100", "box256", "mhrd"]:
            adapter = get_adapter(game)
            assert adapter.game_name == game

    def test_unknown_game_raises(self):
        with pytest.raises(ValueError, match="Unknown game"):
            get_adapter("unknown_game")

    def test_adapters_registry(self):
        assert "hrm" in ADAPTERS
        assert "sic1" in ADAPTERS
        assert "tis100" in ADAPTERS
        assert "box256" in ADAPTERS
        assert "mhrd" in ADAPTERS
