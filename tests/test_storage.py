import kb.storage as storage


def test_ensure_entity_idempotent(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setattr(storage, "DATABASE_PATH", db_path)
    storage.init_db()
    first = storage.ensure_entity("NVDA", "company")
    second = storage.ensure_entity("NVDA", "company")
    assert first == second
