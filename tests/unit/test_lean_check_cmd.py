from __future__ import annotations

from pathlib import Path

from erdos.commands.lean.check_cmd import check_lean_file
from erdos.core.lean_runner import LeanRunner
from erdos.core.models import LeanCheckResult


def test_check_lean_file_normalizes_to_absolute(tmp_path: Path, monkeypatch) -> None:
    project_path = tmp_path / "formal" / "lean"
    (project_path / "Erdos").mkdir(parents=True)
    lean_file = project_path / "Erdos" / "Problem006.lean"
    lean_file.write_text("-- test\n", encoding="utf-8")

    monkeypatch.chdir(tmp_path)

    captured: list[Path] = []

    def fake_check(
        self: LeanRunner, file_path: Path, *, timeout: int = 120
    ) -> LeanCheckResult:
        captured.append(file_path)
        return LeanCheckResult(file=file_path.name, success=True)

    monkeypatch.setattr(LeanRunner, "check", fake_check)

    result = check_lean_file(
        Path("formal/lean/Erdos/Problem006.lean"),
        project_path=Path("formal/lean"),
    )

    assert result.success is True
    assert len(captured) == 1
    assert captured[0].is_absolute()
    assert captured[0] == lean_file
