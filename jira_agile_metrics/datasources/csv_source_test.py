import json
import os
import tempfile

import pandas as pd
import pytest
from pandas import Timestamp

from .csv_source import CSVDataSource
from .offline_loader import load_cycle_data_from_file


@pytest.fixture
def minimal_settings():
    """Minimal settings for CSV data source testing."""
    return {
        "attributes": {},
        "known_values": {},
        "cycle": [
            {"name": "Backlog", "statuses": ["Backlog"]},
            {"name": "Committed", "statuses": ["Next"]},
            {"name": "Build", "statuses": ["Build"]},
            {"name": "Test", "statuses": ["Code review", "QA"]},
            {"name": "Done", "statuses": ["Done"]},
        ],
        "committed_column": "Committed",
        "done_column": "Done",
        "query_attribute": None,
    }


@pytest.fixture
def sample_csv_data():
    """Sample CSV data matching CycleTimeCalculator output format."""
    return """ID,Link,Name,Backlog,Committed,Build,Test,Done,Type,Status,Resolution,Blocked Days
A-1,https://example.org/browse/A-1,First issue,2018-01-01 00:00:00,2018-01-02 00:00:00,2018-01-03 00:00:00,2018-01-04 00:00:00,2018-01-05 00:00:00,Story,Done,Fixed,0
A-2,https://example.org/browse/A-2,Second issue,2018-01-02 00:00:00,2018-01-03 00:00:00,"","",2018-01-06 00:00:00,Bug,Done,Fixed,1
A-3,https://example.org/browse/A-3,Third issue,2018-01-03 00:00:00,2018-01-04 00:00:00,"","","",Story,Committed,"",0
A-4,https://example.org/browse/A-4,Fourth issue,2018-01-04 00:00:00,"","","","",Story,Backlog,"",0"""


@pytest.fixture
def sample_json_data():
    """Sample JSON data matching CycleTimeCalculator output format."""
    return [
        [
            "ID",
            "Link",
            "Name",
            "Backlog",
            "Committed",
            "Build",
            "Test",
            "Done",
            "Type",
            "Status",
            "Resolution",
            "Blocked Days",
        ],
        [
            "A-1",
            "https://example.org/browse/A-1",
            "First issue",
            "2018-01-01 00:00:00",
            "2018-01-02 00:00:00",
            "2018-01-03 00:00:00",
            "2018-01-04 00:00:00",
            "2018-01-05 00:00:00",
            "Story",
            "Done",
            "Fixed",
            0,
        ],
        [
            "A-2",
            "https://example.org/browse/A-2",
            "Second issue",
            "2018-01-02 00:00:00",
            "2018-01-03 00:00:00",
            "",
            "",
            "2018-01-06 00:00:00",
            "Bug",
            "Done",
            "Fixed",
            1,
        ],
        [
            "A-3",
            "https://example.org/browse/A-3",
            "Third issue",
            "2018-01-03 00:00:00",
            "2018-01-04 00:00:00",
            "",
            "",
            "",
            "Story",
            "Committed",
            "",
            0,
        ],
        [
            "A-4",
            "https://example.org/browse/A-4",
            "Fourth issue",
            "2018-01-04 00:00:00",
            "",
            "",
            "",
            "",
            "Story",
            "Backlog",
            "",
            0,
        ],
    ]


@pytest.fixture
def csv_file(sample_csv_data):
    """Create a temporary CSV file with sample data."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write(sample_csv_data)
        f.flush()
        yield f.name
    os.unlink(f.name)


@pytest.fixture
def json_file(sample_json_data):
    """Create a temporary JSON file with sample data."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(sample_json_data, f)
        f.flush()
        yield f.name
    os.unlink(f.name)


class TestCSVDataSource:
    """Test CSV data source functionality."""

    def test_csv_data_source_initialization(self, csv_file, minimal_settings):
        """Test CSVDataSource can be initialized with a CSV file."""
        data_source = CSVDataSource(csv_file, minimal_settings)
        assert data_source is not None

        cycle_data = data_source.get_precomputed_cycle_data()
        assert cycle_data is not None
        assert len(cycle_data) == 4
        assert list(cycle_data["key"]) == ["A-1", "A-2", "A-3", "A-4"]

    def test_json_data_source_initialization(self, json_file, minimal_settings):
        """Test CSVDataSource can be initialized with a JSON file."""
        data_source = CSVDataSource(json_file, minimal_settings)
        assert data_source is not None

        cycle_data = data_source.get_precomputed_cycle_data()
        assert cycle_data is not None
        assert len(cycle_data) == 4
        assert list(cycle_data["key"]) == ["A-1", "A-2", "A-3", "A-4"]

    def test_csv_data_structure(self, csv_file, minimal_settings):
        """Test that CSV data is properly structured after loading."""
        data_source = CSVDataSource(csv_file, minimal_settings)
        cycle_data = data_source.get_precomputed_cycle_data()

        # Check required columns exist
        required_cols = [
            "key",
            "url",
            "summary",
            "issue_type",
            "status",
            "resolution",
            "cycle_time",
            "completed_timestamp",
            "blocked_days",
            "impediments",
            "Backlog",
            "Committed",
            "Build",
            "Test",
            "Done",
        ]
        for col in required_cols:
            assert col in cycle_data.columns, f"Missing column: {col}"

        # Check data types
        assert cycle_data["key"].dtype == "object"
        assert cycle_data["Backlog"].dtype == "datetime64[ns]"
        assert cycle_data["Committed"].dtype == "datetime64[ns]"
        assert cycle_data["blocked_days"].dtype == "int64"
        assert cycle_data["cycle_time"].dtype == "timedelta64[ns]"

    def test_cycle_time_calculation(self, csv_file, minimal_settings):
        """Test that cycle times are calculated correctly from CSV data."""
        data_source = CSVDataSource(csv_file, minimal_settings)
        cycle_data = data_source.get_precomputed_cycle_data()

        # A-1: committed 2018-01-02, done 2018-01-05 = 3 days
        a1_cycle_time = cycle_data[cycle_data["key"] == "A-1"]["cycle_time"].iloc[0]
        assert a1_cycle_time == pd.Timedelta(days=3)

        # A-2: committed 2018-01-03, done 2018-01-06 = 3 days
        a2_cycle_time = cycle_data[cycle_data["key"] == "A-2"]["cycle_time"].iloc[0]
        assert a2_cycle_time == pd.Timedelta(days=3)

        # A-3: committed but not done = NaT
        a3_cycle_time = cycle_data[cycle_data["key"] == "A-3"]["cycle_time"].iloc[0]
        assert pd.isna(a3_cycle_time)

    def test_completed_timestamp_calculation(self, csv_file, minimal_settings):
        """Test that completed timestamps are set correctly."""
        data_source = CSVDataSource(csv_file, minimal_settings)
        cycle_data = data_source.get_precomputed_cycle_data()

        # A-1: done 2018-01-05
        a1_completed = cycle_data[cycle_data["key"] == "A-1"]["completed_timestamp"].iloc[0]
        assert a1_completed == Timestamp("2018-01-05 00:00:00")

        # A-3: not done = NaT
        a3_completed = cycle_data[cycle_data["key"] == "A-3"]["completed_timestamp"].iloc[0]
        assert pd.isna(a3_completed)

    def test_blocked_days_handling(self, csv_file, minimal_settings):
        """Test that blocked days are handled correctly."""
        data_source = CSVDataSource(csv_file, minimal_settings)
        cycle_data = data_source.get_precomputed_cycle_data()

        # A-2 has 1 blocked day
        a2_blocked = cycle_data[cycle_data["key"] == "A-2"]["blocked_days"].iloc[0]
        assert a2_blocked == 1

        # Others have 0 blocked days
        other_blocked = cycle_data[cycle_data["key"] != "A-2"]["blocked_days"].tolist()
        assert all(days == 0 for days in other_blocked)

    def test_impediments_column(self, csv_file, minimal_settings):
        """Test that impediments column is created as empty lists."""
        data_source = CSVDataSource(csv_file, minimal_settings)
        cycle_data = data_source.get_precomputed_cycle_data()

        # All impediments should be empty lists
        for impediments in cycle_data["impediments"]:
            assert isinstance(impediments, list)
            assert len(impediments) == 0

    def test_missing_columns_handled(self, minimal_settings):
        """Test that missing columns are handled gracefully."""
        # Create CSV with minimal columns
        minimal_csv = """ID,Name,Backlog,Done
A-1,Test issue,2018-01-01,2018-01-05"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(minimal_csv)
            f.flush()

            try:
                data_source = CSVDataSource(f.name, minimal_settings)
                cycle_data = data_source.get_precomputed_cycle_data()

                # Missing columns should be filled with None/defaults
                assert cycle_data["url"].iloc[0] is None
                assert cycle_data["issue_type"].iloc[0] is None
                assert cycle_data["blocked_days"].iloc[0] == 0
                assert isinstance(cycle_data["impediments"].iloc[0], list)

            finally:
                os.unlink(f.name)

    def test_empty_file_handling(self, minimal_settings):
        """Test that empty files are handled gracefully."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("ID,Name\n")  # Header only, no data
            f.flush()

            try:
                data_source = CSVDataSource(f.name, minimal_settings)
                cycle_data = data_source.get_precomputed_cycle_data()

                assert cycle_data.empty

            finally:
                os.unlink(f.name)

    def test_invalid_file_format(self, minimal_settings):
        """Test that invalid file formats raise appropriate errors."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("invalid data")
            f.flush()

            try:
                with pytest.raises(ValueError, match="Unsupported cycle data file type"):
                    CSVDataSource(f.name, minimal_settings)

            finally:
                os.unlink(f.name)


class TestOfflineLoader:
    """Test the offline loader functionality directly."""

    def test_load_cycle_data_from_csv(self, csv_file, minimal_settings):
        """Test loading cycle data directly from CSV."""
        df = load_cycle_data_from_file(csv_file, minimal_settings)

        assert len(df) == 4
        assert "key" in df.columns
        assert "cycle_time" in df.columns
        assert df["key"].iloc[0] == "A-1"

    def test_load_cycle_data_from_json(self, json_file, minimal_settings):
        """Test loading cycle data directly from JSON."""
        df = load_cycle_data_from_file(json_file, minimal_settings)

        assert len(df) == 4
        assert "key" in df.columns
        assert "cycle_time" in df.columns
        assert df["key"].iloc[0] == "A-1"

    def test_column_renaming(self, csv_file, minimal_settings):
        """Test that CSV headers are renamed to internal column names."""
        df = load_cycle_data_from_file(csv_file, minimal_settings)

        # Check that external headers are renamed
        assert "key" in df.columns  # was 'ID'
        assert "url" in df.columns  # was 'Link'
        assert "summary" in df.columns  # was 'Name'
        assert "issue_type" in df.columns  # was 'Type'
        assert "blocked_days" in df.columns  # was 'Blocked Days'

        # Original headers should not exist
        assert "ID" not in df.columns
        assert "Link" not in df.columns
        assert "Name" not in df.columns
        assert "Type" not in df.columns
        assert "Blocked Days" not in df.columns

    def test_date_parsing(self, csv_file, minimal_settings):
        """Test that date columns are parsed correctly."""
        df = load_cycle_data_from_file(csv_file, minimal_settings)

        # Check that cycle columns are datetime
        for col in ["Backlog", "Committed", "Build", "Test", "Done"]:
            assert df[col].dtype == "datetime64[ns]"

        # Check specific values
        assert df[df["key"] == "A-1"]["Backlog"].iloc[0] == Timestamp("2018-01-01")
        assert df[df["key"] == "A-1"]["Done"].iloc[0] == Timestamp("2018-01-05")

    def test_missing_cycle_columns(self, minimal_settings):
        """Test handling of missing cycle columns."""
        # CSV missing some cycle columns
        csv_data = """ID,Name,Backlog,Done
A-1,Test,2018-01-01,2018-01-05"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(csv_data)
            f.flush()

            try:
                df = load_cycle_data_from_file(f.name, minimal_settings)

                # Missing columns should be NaT
                assert pd.isna(df["Committed"].iloc[0])
                assert pd.isna(df["Build"].iloc[0])
                assert pd.isna(df["Test"].iloc[0])

                # Present columns should be parsed
                assert df["Backlog"].iloc[0] == Timestamp("2018-01-01")
                assert df["Done"].iloc[0] == Timestamp("2018-01-05")

            finally:
                os.unlink(f.name)
