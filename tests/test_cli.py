import pytest

from app.cli import main


def test_hearing_prints_every_duck_and_a_finding(capsys: pytest.CaptureFixture[str]) -> None:
    main(
        [
            "My flatmate eats my food.",
            "Hide a ghost pepper in it.",
            "--fast",
            "--ducks",
            "doctor,rich,rebel",
        ]
    )
    out = capsys.readouterr().out
    for name in ("Dr. Beakman Quackson, MD", "Sir Bill Quackington IV", "Flare"):
        assert name in out
    assert "THE COUNCIL FINDS" in out


def test_list_shows_all_thirteen(capsys: pytest.CaptureFixture[str]) -> None:
    main(["--list"])
    assert len(capsys.readouterr().out.strip().splitlines()) == 13


def test_unknown_duck_is_a_clear_error() -> None:
    with pytest.raises(SystemExit, match="unknown duck"):
        main(["s", "a", "--ducks", "platypus"])
