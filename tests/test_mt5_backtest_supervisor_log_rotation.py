from pathlib import Path

from app.workers import mt5_backtest_supervisor as supervisor


def test_supervisor_log_rotation_bounds_disk_growth(tmp_path, monkeypatch):
    log_path = tmp_path / "supervisor.log"
    monkeypatch.setattr(supervisor, "LOG", log_path)
    monkeypatch.setattr(supervisor, "LOG_MAX_BYTES", 16)
    monkeypatch.setattr(supervisor, "LOG_BACKUP_COUNT", 3)

    log_path.write_text("x" * 20, encoding="utf-8")
    for index in range(1, 4):
        log_path.with_name(f"supervisor.log.{index}").write_text(f"previous-{index}", encoding="utf-8")

    supervisor.log("new entry")

    assert log_path.read_text(encoding="utf-8").endswith("new entry\n")
    assert log_path.with_name("supervisor.log.1").read_text(encoding="utf-8") == "x" * 20
    assert log_path.with_name("supervisor.log.2").read_text(encoding="utf-8") == "previous-1"
    assert log_path.with_name("supervisor.log.3").read_text(encoding="utf-8") == "previous-2"
    assert not log_path.with_name("supervisor.log.4").exists()
