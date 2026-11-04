from app.db.migration import include_name, target_metadata


def test_unmanaged_tables_are_excluded() -> None:
    assert not include_name("infra_test", "table", {"schema_qualified_table_name": "infra_test"})
    assert not include_name("unrelated", "table", {})
    assert not include_name("users", "table", {"schema_qualified_table_name": "other.users"})


def test_all_models_are_registered_and_included() -> None:
    expected = {"users", "presentations", "rehearsals", "analysis_jobs", "live_sessions"}
    assert set(target_metadata.tables) == expected
    for name in expected:
        assert include_name(name, "table", {"schema_qualified_table_name": name})
    assert include_name("email", "column", {"table_name": "users"})
