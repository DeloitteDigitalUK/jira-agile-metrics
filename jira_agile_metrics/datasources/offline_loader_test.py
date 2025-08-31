from unittest.mock import patch

import pandas as pd
import pytest

from .offline_loader import _parse_dates_robust, load_cycle_data_from_file


class TestRobustDateParsing:
    """Test robust date parsing for different formats and locales."""

    def test_iso_format_dates(self):
        """Test ISO format dates (tool-generated CSV files)."""
        dates = pd.Series(["2019-02-08", "2019-02-11", "2019-01-15"])
        result = _parse_dates_robust(dates)

        assert not result.isna().any(), "All ISO dates should parse successfully"
        assert result[0] == pd.Timestamp("2019-02-08")
        assert result[1] == pd.Timestamp("2019-02-11")
        assert result[2] == pd.Timestamp("2019-01-15")

    def test_dd_mm_yyyy_format_dates(self):
        """Test DD/MM/YYYY format dates (European/UK format)."""
        dates = pd.Series(["08/02/2019", "11/02/2019", "15/01/2019"])
        result = _parse_dates_robust(dates)

        assert not result.isna().any(), "All DD/MM/YYYY dates should parse successfully"
        assert result[0] == pd.Timestamp("2019-02-08")
        assert result[1] == pd.Timestamp("2019-02-11")
        assert result[2] == pd.Timestamp("2019-01-15")

    def test_mm_dd_yyyy_format_dates(self):
        """Test MM/DD/YYYY format dates (US format)."""
        dates = pd.Series(["02/08/2019", "02/11/2019", "01/15/2019"])
        result = _parse_dates_robust(dates)

        assert not result.isna().any(), "All MM/DD/YYYY dates should parse successfully"
        assert result[0] == pd.Timestamp("2019-02-08")
        assert result[1] == pd.Timestamp("2019-02-11")
        assert result[2] == pd.Timestamp("2019-01-15")

    def test_mixed_format_dates_iso_priority(self):
        """Test that ISO format takes priority in mixed format scenarios."""
        # All ISO format dates - should be detected and used
        dates = pd.Series(["2019-01-15", "2019-01-16", "2019-01-17"])

        with patch("jira_agile_metrics.datasources.offline_loader.logger") as mock_logger:
            result = _parse_dates_robust(dates)

            # Should use ISO format parsing (100% success)
            mock_logger.debug.assert_called_with("Parsed dates using ISO format (YYYY-MM-DD)")

            expected = pd.Series([pd.Timestamp("2019-01-15"), pd.Timestamp("2019-01-16"), pd.Timestamp("2019-01-17")])
            pd.testing.assert_series_equal(result, expected)

    def test_mixed_format_dates_dd_mm_priority(self):
        """Test DD/MM/YYYY format detection with mixed data."""
        # All DD/MM/YYYY format dates - should be detected and used
        dates = pd.Series(["15/01/2019", "16/01/2019", "17/01/2019"])

        with patch("jira_agile_metrics.datasources.offline_loader.logger") as mock_logger:
            result = _parse_dates_robust(dates)

            # Should use DD/MM/YYYY format parsing (100% success)
            mock_logger.debug.assert_called_with("Parsed dates using DD/MM/YYYY format")

            expected = pd.Series([pd.Timestamp("2019-01-15"), pd.Timestamp("2019-01-16"), pd.Timestamp("2019-01-17")])
            pd.testing.assert_series_equal(result, expected)

    def test_empty_and_null_dates(self):
        """Test handling of empty and null date series."""
        # All null
        dates = pd.Series([None, None, None])
        result = _parse_dates_robust(dates)
        assert result.isna().all()

        # Empty series
        dates = pd.Series([], dtype=object)
        result = _parse_dates_robust(dates)
        assert len(result) == 0

        # Mix of null and valid dates
        dates = pd.Series(["2019-02-08", None, "2019-02-11"])
        result = _parse_dates_robust(dates)
        assert result[0] == pd.Timestamp("2019-02-08")
        assert pd.isna(result[1])
        assert result[2] == pd.Timestamp("2019-02-11")

    def test_invalid_dates(self):
        """Test handling of invalid date strings."""
        dates = pd.Series(["invalid", "not-a-date", "99/99/9999"])
        result = _parse_dates_robust(dates)

        # Should fall back to dayfirst=True parsing, but still fail for invalid dates
        assert result.isna().all()

    def test_ambiguous_dates_fallback(self):
        """Test fallback behavior for ambiguous date formats."""
        # Dates that could be either MM/DD or DD/MM - use dates that will fail specific format parsing
        dates = pd.Series(["32/01/2019", "33/02/2019", "34/03/2019"])  # Invalid days to force fallback

        with patch("jira_agile_metrics.datasources.offline_loader.logger") as mock_logger:
            result = _parse_dates_robust(dates)

            # Should eventually use fallback with dayfirst=True
            mock_logger.warning.assert_called_with("Using fallback date parsing with dayfirst=True")

            # These dates are invalid, so should result in NaT
            expected = pd.Series([pd.NaT, pd.NaT, pd.NaT])
            pd.testing.assert_series_equal(result, expected)


class TestCSVDataLoading:
    """Test CSV data loading with different date formats."""

    @pytest.fixture
    def minimal_settings(self):
        return {
            "cycle": [
                {"name": "Backlog", "statuses": ["Backlog"]},
                {"name": "Next", "statuses": ["Next"]},
                {"name": "Done", "statuses": ["Done"]},
            ],
            "committed_column": "Next",
            "done_column": "Done",
            "attributes": {},
            "query_attribute": None,
        }

    def test_iso_format_csv_loading(self, tmp_path, minimal_settings):
        """Test loading CSV with ISO format dates (YYYY-MM-DD)."""
        csv_content = """ID,Link,Name,Backlog,Next,Done,Type,Status,Resolution,Blocked Days
A-1,http://example.com/A-1,Test Issue,2019-01-01,2019-01-02,2019-01-05,Story,Done,Fixed,0
A-2,http://example.com/A-2,Another Issue,2019-01-02,2019-01-03,2019-01-06,Bug,Done,Fixed,1"""

        csv_file = tmp_path / "test_iso.csv"
        csv_file.write_text(csv_content)

        df = load_cycle_data_from_file(str(csv_file), minimal_settings)

        assert len(df) == 2
        assert df["completed_timestamp"].notna().all()
        assert df["cycle_time"].notna().all()
        assert df.loc[0, "cycle_time"] == pd.Timedelta(days=3)  # Next to Done: 2019-01-02 to 2019-01-05 = 3 days
        assert df.loc[1, "cycle_time"] == pd.Timedelta(days=3)  # Next to Done: 2019-01-03 to 2019-01-06 = 3 days

    def test_dd_mm_yyyy_format_csv_loading(self, tmp_path, minimal_settings):
        """Test loading CSV with DD/MM/YYYY format dates (European format)."""
        csv_content = """ID,Link,Name,Backlog,Next,Done,Type,Status,Resolution,Blocked Days
A-1,http://example.com/A-1,Test Issue,01/01/2019,02/01/2019,05/01/2019,Story,Done,Fixed,0
A-2,http://example.com/A-2,Another Issue,02/01/2019,03/01/2019,06/01/2019,Bug,Done,Fixed,1"""

        csv_file = tmp_path / "test_ddmm.csv"
        csv_file.write_text(csv_content)

        df = load_cycle_data_from_file(str(csv_file), minimal_settings)

        assert len(df) == 2
        assert df["completed_timestamp"].notna().all()
        assert df["cycle_time"].notna().all()
        assert df.loc[0, "cycle_time"] == pd.Timedelta(days=3)  # Next to Done: 02/01 to 05/01 = 3 days
        assert df.loc[1, "cycle_time"] == pd.Timedelta(days=3)  # Next to Done: 03/01 to 06/01 = 3 days

    def test_mm_dd_yyyy_format_csv_loading(self, tmp_path, minimal_settings):
        """Test loading CSV with MM/DD/YYYY format dates (US format)."""
        csv_content = """ID,Link,Name,Backlog,Next,Done,Type,Status,Resolution,Blocked Days
A-1,http://example.com/A-1,Test Issue,01/01/2019,02/01/2019,05/01/2019,Story,Done,Fixed,0
A-2,http://example.com/A-2,Another Issue,02/01/2019,03/01/2019,06/01/2019,Bug,Done,Fixed,1"""

        csv_file = tmp_path / "test_mmdd.csv"
        csv_file.write_text(csv_content)

        df = load_cycle_data_from_file(str(csv_file), minimal_settings)

        assert len(df) == 2
        assert df["completed_timestamp"].notna().all()
        assert df["cycle_time"].notna().all()
        assert df.loc[0, "cycle_time"] == pd.Timedelta(days=3)  # Next to Done: 02/01 to 05/01 = 3 days
        assert df.loc[1, "cycle_time"] == pd.Timedelta(days=3)  # Next to Done: 03/01 to 06/01 = 3 days

    def test_regression_date_parsing_consistency(self, tmp_path, minimal_settings):
        """Regression test to ensure date parsing doesn't break with format changes."""
        # Test that each format can be parsed correctly (not necessarily to same logical dates)
        test_cases = [
            # ISO format (tool default)
            {
                "dates": ("2019-02-08", "2019-02-11", "2019-02-15"),
                "expected": [pd.Timestamp("2019-02-08"), pd.Timestamp("2019-02-11"), pd.Timestamp("2019-02-15")],
                "cycle_time": 4,
            },
            # DD/MM/YYYY format (European) - unambiguous dates
            {
                "dates": ("20/02/2019", "23/02/2019", "27/02/2019"),
                "expected": [pd.Timestamp("2019-02-20"), pd.Timestamp("2019-02-23"), pd.Timestamp("2019-02-27")],
                "cycle_time": 4,
            },
            # MM/DD/YYYY format (US) - unambiguous dates
            {
                "dates": ("02/20/2019", "02/23/2019", "02/27/2019"),
                "expected": [pd.Timestamp("2019-02-20"), pd.Timestamp("2019-02-23"), pd.Timestamp("2019-02-27")],
                "cycle_time": 4,
            },
        ]

        for i, test_case in enumerate(test_cases):
            backlog_date, next_date, done_date = test_case["dates"]
            expected_dates = test_case["expected"]
            expected_cycle_time = test_case["cycle_time"]

            csv_content = f"""ID,Link,Name,Backlog,Next,Done,Type,Status,Resolution,Blocked Days
A-1,http://example.com/A-1,Test Issue,{backlog_date},{next_date},{done_date},Story,Done,Fixed,0"""

            csv_file = tmp_path / f"test_format_{i}.csv"
            csv_file.write_text(csv_content)

            df = load_cycle_data_from_file(str(csv_file), minimal_settings)

            # Each format should parse correctly
            assert len(df) == 1
            assert df.loc[0, "Backlog"] == expected_dates[0]
            assert df.loc[0, "Next"] == expected_dates[1]
            assert df.loc[0, "Done"] == expected_dates[2]
            assert df.loc[0, "completed_timestamp"] == expected_dates[2]
            assert df.loc[0, "cycle_time"] == pd.Timedelta(days=expected_cycle_time)
