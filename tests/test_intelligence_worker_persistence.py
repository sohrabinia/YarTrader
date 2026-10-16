import json

from app.workers.intelligence_worker import IntelligenceWorker


class FakeMemory:
    def load_all(self):
        return None

    def get_learning_statistics(self):
        return {
            "total_experiences": 1,
            "patterns_created": 0,
            "concepts_learned": 0,
            "successful_patterns": 0,
            "failed_patterns": 0,
            "last_learning_update": None,
        }

    def promote_experiences_to_patterns(self):
        return []

    def consolidate_patterns_to_concepts(self, **kwargs):
        return []

    def get_patterns(self):
        return []


def test_intelligence_report_persists_when_windows_replace_is_denied(tmp_path, monkeypatch):
    import os
    import src.Research.Brain.active_learning as active_learning

    class FakeActiveLearningEngine:
        def analyze_weaknesses_and_set_priorities(self, patterns):
            return []

    def deny_replace(src, dst):
        raise PermissionError("simulated Windows destination sharing restriction")

    monkeypatch.setattr(active_learning, "ActiveLearningEngine", FakeActiveLearningEngine)
    monkeypatch.setattr(os, "replace", deny_replace)

    target = tmp_path / "active_learning_priorities.json"
    target.write_text('{"old": true}', encoding="utf-8")
    worker = IntelligenceWorker(memory_system=FakeMemory(), report_path=str(target))
    report = worker.run_cycle()

    persisted = json.loads(target.read_text(encoding="utf-8"))
    assert report["status"] == "COMPLETED"
    assert persisted["status"] == "COMPLETED"
    assert persisted["data_source"] == "PERSISTED_BRAIN_MEMORY"
    assert not list(tmp_path.glob("*.tmp"))
