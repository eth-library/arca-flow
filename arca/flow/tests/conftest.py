import pytest


@pytest.fixture(autouse=True)
def dagster_temp_home(tmp_path, monkeypatch):
    """Use system temp directory for Dagster home during tests."""
    monkeypatch.setenv("DAGSTER_HOME", str(tmp_path / "dagster_home"))
