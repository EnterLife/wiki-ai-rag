from datetime import UTC, datetime, timedelta

from wiki_ai_rag_api.services.scheduler import should_index_source


def test_manual_source_is_not_due_for_scheduled_indexing() -> None:
    source = {
        "enabled": True,
        "schedule": {"mode": "manual"},
        "last_indexed_at": None,
    }

    assert should_index_source(source, datetime.now(UTC)) is False


def test_scheduled_source_without_previous_index_is_due() -> None:
    source = {
        "enabled": True,
        "schedule": {"mode": "scheduled", "interval_hours": 6},
        "last_indexed_at": None,
    }

    assert should_index_source(source, datetime.now(UTC)) is True


def test_recently_indexed_source_is_not_due() -> None:
    now = datetime(2026, 6, 21, 12, 0, tzinfo=UTC)
    source = {
        "enabled": True,
        "schedule": {"mode": "scheduled", "interval_hours": 6},
        "last_indexed_at": (now - timedelta(hours=2)).isoformat(),
    }

    assert should_index_source(source, now) is False


def test_old_indexed_source_is_due() -> None:
    now = datetime(2026, 6, 21, 12, 0, tzinfo=UTC)
    source = {
        "enabled": True,
        "schedule": {"mode": "scheduled", "interval_hours": 6},
        "last_indexed_at": (now - timedelta(hours=8)).isoformat(),
    }

    assert should_index_source(source, now) is True

