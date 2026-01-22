"""Tests for loop configuration."""

import pytest

from erdos.core.loop.config import LoopConfig


class TestLoopConfigDefaults:
    """Test default configuration values."""

    def test_default_max_iterations(self) -> None:
        config = LoopConfig()
        assert config.max_iterations == 10

    def test_default_max_patch_lines(self) -> None:
        config = LoopConfig()
        assert config.max_patch_lines == 50

    def test_default_max_patch_bytes(self) -> None:
        config = LoopConfig()
        assert config.max_patch_bytes == 8192

    def test_default_max_file_bytes_prompt(self) -> None:
        config = LoopConfig()
        assert config.max_file_bytes_prompt == 16384

    def test_default_max_prompt_bytes(self) -> None:
        config = LoopConfig()
        assert config.max_prompt_bytes == 32768

    def test_default_stall_threshold(self) -> None:
        config = LoopConfig()
        assert config.stall_threshold == 3

    def test_default_lean_timeout_seconds(self) -> None:
        config = LoopConfig()
        assert config.lean_timeout_seconds == 120

    def test_default_min_file_size_ratio(self) -> None:
        config = LoopConfig()
        assert config.min_file_size_ratio == 0.8

    def test_default_allow_sorry_increase(self) -> None:
        config = LoopConfig()
        assert config.allow_sorry_increase == 0

    def test_default_rag_limit(self) -> None:
        config = LoopConfig()
        assert config.rag_limit == 5


class TestLoopConfigCustomValues:
    """Test creating config with custom values."""

    def test_custom_max_iterations(self) -> None:
        config = LoopConfig(max_iterations=20)
        assert config.max_iterations == 20

    def test_custom_max_patch_lines(self) -> None:
        config = LoopConfig(max_patch_lines=100)
        assert config.max_patch_lines == 100

    def test_custom_allow_sorry_increase(self) -> None:
        config = LoopConfig(allow_sorry_increase=2)
        assert config.allow_sorry_increase == 2


class TestLoopConfigFromCli:
    """Test config creation from CLI options."""

    def test_from_cli_with_overrides(self) -> None:
        config = LoopConfig.from_cli(max_iterations=5, max_patch_lines=25)
        assert config.max_iterations == 5
        assert config.max_patch_lines == 25
        # Other values remain default
        assert config.max_patch_bytes == 8192

    def test_from_cli_filters_none_values(self) -> None:
        config = LoopConfig.from_cli(max_iterations=5, max_patch_lines=None)
        assert config.max_iterations == 5
        assert config.max_patch_lines == 50  # default

    def test_from_cli_with_no_overrides(self) -> None:
        config = LoopConfig.from_cli()
        assert config == LoopConfig()


class TestLoopConfigImmutability:
    """Test that config is immutable."""

    def test_cannot_modify_after_creation(self) -> None:
        config = LoopConfig()
        with pytest.raises(AttributeError):
            config.max_iterations = 20  # type: ignore[misc]
