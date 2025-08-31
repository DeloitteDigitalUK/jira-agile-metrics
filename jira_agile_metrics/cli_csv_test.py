import os
import tempfile
from unittest import mock
from unittest.mock import Mock, patch

import pytest

from .calculators.cycletime import CycleTimeCalculator
from .calculators.debt import DebtCalculator
from .calculators.defects import DefectsCalculator
from .calculators.progressreport import ProgressReportCalculator
from .calculators.waste import WasteCalculator
from .cli import configure_argument_parser, run_command_line, validate_csv_calculator_compatibility
from .config import ConfigError


@pytest.fixture
def minimal_config():
    """Minimal configuration for testing CSV functionality."""
    return """
Connection:
  Type: jira
  Domain: https://example.jira.com

Query: project = "TEST"

Workflow:
  Backlog: Backlog
  Committed: Next
  Build: Build
  Test: Test
  Done: Done

Output:
  Cycle time data:
    - cycletime.csv
"""


@pytest.fixture
def config_with_unsafe_calculators():
    """Configuration that includes unsafe calculators for CSV mode."""
    return """
Connection:
  Type: jira
  Domain: https://example.jira.com

Query: project = "TEST"

Workflow:
  Backlog: Backlog
  Committed: Next
  Build: Build
  Test: Test
  Done: Done

Output:
  Cycle time data:
    - cycletime.csv
  Defects query: project = "TEST" AND type = "Bug"
  Defects priority field: Priority
  Defects type field: Issue Type
  Defects environment field: Environment
  Debt query: project = "TEST" AND labels = "tech-debt"
  Debt priority field: Priority
  Waste query: project = "TEST" AND resolution = "Won't Do"
  Progress report: progress.html
"""


@pytest.fixture
def sample_csv_data():
    """Sample CSV data for testing."""
    return """ID,Link,Name,Backlog,Committed,Build,Test,Done,Type,Status,Resolution,Blocked Days
A-1,https://example.org/browse/A-1,First issue,2018-01-01 00:00:00,2018-01-02 00:00:00,2018-01-03 00:00:00,2018-01-04 00:00:00,2018-01-05 00:00:00,Story,Done,Fixed,0
A-2,https://example.org/browse/A-2,Second issue,2018-01-02 00:00:00,2018-01-03 00:00:00,,,2018-01-06 00:00:00,Bug,Done,Fixed,1"""


@pytest.fixture
def csv_file(sample_csv_data):
    """Create a temporary CSV file with sample data."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write(sample_csv_data)
        f.flush()
        yield f.name
    os.unlink(f.name)


class TestCSVCalculatorValidation:
    """Test validation of calculator compatibility with CSV mode."""

    def test_validate_safe_calculators(self):
        """Test that safe calculators pass validation."""
        calculators = [CycleTimeCalculator]
        settings = {}

        # Should not raise any exception
        validate_csv_calculator_compatibility(calculators, settings)

    def test_validate_unsafe_calculators_not_configured(self):
        """Test that unsafe calculators pass validation when not configured."""
        calculators = [DefectsCalculator, DebtCalculator, WasteCalculator, ProgressReportCalculator]
        settings = {}  # No settings that would enable these calculators

        # Should not raise any exception since calculators aren't configured
        validate_csv_calculator_compatibility(calculators, settings)

    def test_validate_defects_calculator_configured(self):
        """Test that DefectsCalculator fails validation when configured."""
        calculators = [DefectsCalculator]
        settings = {"defects_query": "project = TEST AND type = Bug"}

        with pytest.raises(ConfigError) as exc_info:
            validate_csv_calculator_compatibility(calculators, settings)

        error_msg = str(exc_info.value)
        assert "Cannot use --cycle-data-file with calculators that require JIRA connectivity" in error_msg
        assert "DefectsCalculator" in error_msg
        assert "defects_query" in error_msg

    def test_validate_debt_calculator_configured(self):
        """Test that DebtCalculator fails validation when configured."""
        calculators = [DebtCalculator]
        settings = {"debt_query": "project = TEST AND labels = tech-debt"}

        with pytest.raises(ConfigError) as exc_info:
            validate_csv_calculator_compatibility(calculators, settings)

        error_msg = str(exc_info.value)
        assert "DebtCalculator" in error_msg
        assert "debt_query" in error_msg

    def test_validate_waste_calculator_configured(self):
        """Test that WasteCalculator fails validation when configured."""
        calculators = [WasteCalculator]
        settings = {"waste_query": 'project = TEST AND resolution = "Won\'t Do"'}

        with pytest.raises(ConfigError) as exc_info:
            validate_csv_calculator_compatibility(calculators, settings)

        error_msg = str(exc_info.value)
        assert "WasteCalculator" in error_msg
        assert "waste_query" in error_msg

    def test_validate_progress_report_configured(self):
        """Test that ProgressReportCalculator fails validation when configured."""
        calculators = [ProgressReportCalculator]
        settings = {"progress_report": "progress.html"}

        with pytest.raises(ConfigError) as exc_info:
            validate_csv_calculator_compatibility(calculators, settings)

        error_msg = str(exc_info.value)
        assert "ProgressReportCalculator" in error_msg
        assert "progress_report" in error_msg

    def test_validate_multiple_unsafe_calculators(self):
        """Test validation with multiple unsafe calculators configured."""
        calculators = [DefectsCalculator, DebtCalculator, WasteCalculator]
        settings = {
            "defects_query": "project = TEST AND type = Bug",
            "debt_query": "project = TEST AND labels = tech-debt",
            "waste_query": 'project = TEST AND resolution = "Won\'t Do"',
        }

        with pytest.raises(ConfigError) as exc_info:
            validate_csv_calculator_compatibility(calculators, settings)

        error_msg = str(exc_info.value)
        assert "DefectsCalculator" in error_msg
        assert "DebtCalculator" in error_msg
        assert "WasteCalculator" in error_msg

    def test_validation_error_message_format(self):
        """Test that validation error messages are user-friendly."""
        calculators = [DefectsCalculator]
        settings = {"defects_query": "project = TEST"}

        with pytest.raises(ConfigError) as exc_info:
            validate_csv_calculator_compatibility(calculators, settings)

        error_msg = str(exc_info.value)

        # Check error message contains helpful information
        assert "Cannot use --cycle-data-file" in error_msg
        assert "JIRA connectivity" in error_msg
        assert "Remove/comment out" in error_msg
        assert "Run without --cycle-data-file" in error_msg
        assert "Compatible calculators include" in error_msg


class TestCLICSVIntegration:
    """Test CLI integration with CSV data sources."""

    @patch("jira_agile_metrics.cli.run_calculators")
    @patch("jira_agile_metrics.cli.QueryManager")
    @patch("jira_agile_metrics.cli.CSVDataSource")
    def test_cli_with_csv_file_safe_config(
        self, mock_csv_source, mock_query_manager, mock_run_calculators, csv_file, minimal_config
    ):
        """Test CLI execution with CSV file and safe configuration."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as config_file:
            config_file.write(minimal_config)
            config_file.flush()

            try:
                parser = configure_argument_parser()
                args = parser.parse_args([config_file.name, "--cycle-data-file", csv_file])

                # Should not raise any exception
                run_command_line(parser, args)

                # Verify CSV data source was created
                mock_csv_source.assert_called_once_with(csv_file, mock.ANY)

                # Verify QueryManager was created with data source
                mock_query_manager.assert_called_once()
                call_args = mock_query_manager.call_args
                assert call_args[0][0] is None  # jira client should be None
                assert call_args[1]["data_source"] is not None  # data_source should be set

                # Verify calculators were run
                mock_run_calculators.assert_called_once()

            finally:
                os.unlink(config_file.name)

    @patch("jira_agile_metrics.cli.run_calculators")
    @patch("jira_agile_metrics.cli.QueryManager")
    @patch("jira_agile_metrics.cli.CSVDataSource")
    def test_cli_with_csv_file_unsafe_config(
        self, mock_csv_source, mock_query_manager, mock_run_calculators, csv_file, config_with_unsafe_calculators
    ):
        """Test CLI execution with CSV file and unsafe configuration."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as config_file:
            config_file.write(config_with_unsafe_calculators)
            config_file.flush()

            try:
                parser = configure_argument_parser()
                args = parser.parse_args([config_file.name, "--cycle-data-file", csv_file])

                # Should raise ConfigError due to unsafe calculators
                with pytest.raises(ConfigError) as exc_info:
                    run_command_line(parser, args)

                error_msg = str(exc_info.value)
                assert "Cannot use --cycle-data-file" in error_msg

            finally:
                os.unlink(config_file.name)

    @patch("jira_agile_metrics.cli.run_calculators")
    @patch("jira_agile_metrics.cli.QueryManager")
    @patch("jira_agile_metrics.cli.get_jira_client")
    def test_cli_without_csv_file_unsafe_config(
        self, mock_get_jira_client, mock_query_manager, mock_run_calculators, config_with_unsafe_calculators
    ):
        """Test CLI execution without CSV file but with unsafe configuration (should work)."""
        mock_jira = Mock()
        mock_jira.fields.return_value = [{"id": "summary", "name": "Summary"}]  # Mock fields response
        mock_get_jira_client.return_value = mock_jira

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as config_file:
            config_file.write(config_with_unsafe_calculators)
            config_file.flush()

            try:
                parser = configure_argument_parser()
                args = parser.parse_args([config_file.name])

                # Should not raise any exception since we're not using CSV mode
                run_command_line(parser, args)

                # Verify JIRA client was created
                mock_get_jira_client.assert_called_once()

                # Verify calculators were run
                mock_run_calculators.assert_called_once()

            finally:
                os.unlink(config_file.name)

    def test_csv_file_not_found(self, minimal_config):
        """Test CLI behavior when CSV file doesn't exist."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as config_file:
            config_file.write(minimal_config)
            config_file.flush()

            try:
                parser = configure_argument_parser()
                args = parser.parse_args([config_file.name, "--cycle-data-file", "/nonexistent/file.csv"])

                # Should raise an exception when trying to read the file
                with pytest.raises((FileNotFoundError, OSError)):
                    run_command_line(parser, args)

            finally:
                os.unlink(config_file.name)


class TestQueryManagerCSVIntegration:
    """Test QueryManager integration with CSV data sources."""

    def test_query_manager_with_csv_data_source(self, csv_file):
        """Test QueryManager behavior with CSV data source."""
        from .datasources.csv_source import CSVDataSource
        from .querymanager import QueryManager

        settings = {
            "attributes": {},
            "known_values": {},
            "cycle": [
                {"name": "Backlog", "statuses": ["Backlog"]},
                {"name": "Committed", "statuses": ["Next"]},
                {"name": "Build", "statuses": ["Build"]},
                {"name": "Test", "statuses": ["Test"]},
                {"name": "Done", "statuses": ["Done"]},
            ],
            "committed_column": "Committed",
            "done_column": "Done",
        }

        data_source = CSVDataSource(csv_file, settings)
        query_manager = QueryManager(None, settings, data_source=data_source)

        # Test precomputed data methods
        assert query_manager.has_precomputed_cycle_data()

        cycle_data = query_manager.get_precomputed_cycle_data()
        assert cycle_data is not None
        assert len(cycle_data) == 2
        assert "key" in cycle_data.columns

    def test_query_manager_without_csv_data_source(self):
        """Test QueryManager behavior without CSV data source."""
        from .conftest import FauxJIRA
        from .querymanager import QueryManager

        settings = {"attributes": {}, "known_values": {}}
        jira = FauxJIRA(fields=[{"id": "summary", "name": "Summary"}], issues=[])
        query_manager = QueryManager(jira, settings)

        # Test precomputed data methods
        assert not query_manager.has_precomputed_cycle_data()
        assert query_manager.get_precomputed_cycle_data() is None


class TestCycleTimeCalculatorCSVIntegration:
    """Test CycleTimeCalculator integration with CSV data sources."""

    def test_cycle_time_calculator_with_csv_data(self, csv_file):
        """Test CycleTimeCalculator uses precomputed data when available."""
        from .calculators.cycletime import CycleTimeCalculator
        from .datasources.csv_source import CSVDataSource
        from .querymanager import QueryManager

        settings = {
            "attributes": {},
            "known_values": {},
            "cycle": [
                {"name": "Backlog", "statuses": ["Backlog"]},
                {"name": "Committed", "statuses": ["Next"]},
                {"name": "Build", "statuses": ["Build"]},
                {"name": "Test", "statuses": ["Test"]},
                {"name": "Done", "statuses": ["Done"]},
            ],
            "committed_column": "Committed",
            "done_column": "Done",
            "queries": [{"jql": "project = TEST"}],
            "query_attribute": None,
        }

        data_source = CSVDataSource(csv_file, settings)
        query_manager = QueryManager(None, settings, data_source=data_source)

        calculator = CycleTimeCalculator(query_manager, settings, {})
        result = calculator.run()

        # Should return the precomputed data
        assert result is not None
        assert len(result) == 2
        assert "key" in result.columns
        assert list(result["key"]) == ["A-1", "A-2"]

    def test_cycle_time_calculator_without_csv_data(self):
        """Test CycleTimeCalculator falls back to normal calculation without CSV data."""
        from .calculators.cycletime import CycleTimeCalculator
        from .conftest import FauxJIRA
        from .querymanager import QueryManager

        settings = {
            "attributes": {},
            "known_values": {},
            "cycle": [
                {"name": "Backlog", "statuses": ["Backlog"]},
                {"name": "Committed", "statuses": ["Next"]},
                {"name": "Done", "statuses": ["Done"]},
            ],
            "committed_column": "Committed",
            "done_column": "Done",
            "queries": [{"jql": "project = TEST"}],
            "query_attribute": None,
        }

        jira = FauxJIRA(fields=[{"id": "summary", "name": "Summary"}], issues=[])
        query_manager = QueryManager(jira, settings)

        calculator = CycleTimeCalculator(query_manager, settings, {})

        # Should call the normal calculation path (which will return empty data with no issues)
        result = calculator.run()
        assert result is not None
        assert len(result) == 0  # No issues in our fake JIRA


class TestCSVErrorHandling:
    """Test error handling in CSV functionality."""

    def test_invalid_csv_format(self, minimal_config):
        """Test handling of invalid CSV format."""
        invalid_csv = "invalid,csv,data\nwith,wrong,format"

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as csv_file:
            csv_file.write(invalid_csv)
            csv_file.flush()

            try:
                # Should handle the error gracefully when creating CSVDataSource
                from .datasources.csv_source import CSVDataSource

                settings = {
                    "cycle": [{"name": "Done", "statuses": ["Done"]}],
                    "committed_column": "Committed",
                    "done_column": "Done",
                }

                # This should work - the CSV will be parsed but won't have expected columns
                data_source = CSVDataSource(csv_file.name, settings)
                cycle_data = data_source.get_precomputed_cycle_data()

                # Should have the data but with missing/default columns
                assert cycle_data is not None

            finally:
                os.unlink(csv_file.name)

    def test_empty_csv_file(self, minimal_config):
        """Test handling of empty CSV file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as csv_file:
            csv_file.write("ID,Name\n")  # Header only, no data
            csv_file.flush()

            try:
                # Should handle empty file gracefully
                from .datasources.csv_source import CSVDataSource

                settings = {
                    "cycle": [{"name": "Done", "statuses": ["Done"]}],
                    "committed_column": "Committed",
                    "done_column": "Done",
                }

                data_source = CSVDataSource(csv_file.name, settings)
                cycle_data = data_source.get_precomputed_cycle_data()

                assert cycle_data.empty

            finally:
                os.unlink(csv_file.name)
