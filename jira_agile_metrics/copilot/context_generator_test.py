"""
Unit tests for AI context generator - Flow Metrics focused.
"""

from unittest.mock import Mock, patch

import pandas as pd
import pytest

from .context_generator import AIContextGenerator


@pytest.fixture
def mock_query_manager():
    """Create a mock query manager."""
    mock_qm = Mock()
    mock_qm.get_field_id.return_value = "customfield_001"
    return mock_qm


@pytest.fixture
def test_settings():
    """Test settings for flow analysis."""
    return {
        "team_field": "Team",
        "jira_query": 'project = PROJ AND team = "Alpha Team"',
        "committed_column": "In Progress",
        "done_column": "Done",
        "backlog_column": "To Do",
        "throughput_frequency": "weekly",
        "cycle": [
            {"name": "To Do", "type": "backlog"},
            {"name": "In Progress", "type": "committed"},
            {"name": "Done", "type": "done"},
        ],
        "workflow": {
            "todo": ["To Do", "Backlog"],
            "in_progress": ["In Progress", "Code Review"],
            "done": ["Done", "Closed"],
        },
    }


class TestAIContextGenerator:
    """Test flow-focused context generator."""

    def test_init(self, mock_query_manager, test_settings):
        generator = AIContextGenerator(mock_query_manager, test_settings, {})

        assert generator.query_manager == mock_query_manager

    # AI pattern detection tests removed - functionality moved to InsightsGenerator

    def test_collect_raw_data_success(self, mock_query_manager, test_settings):
        """Test raw data collection from calculators."""
        # Mock calculator results
        mock_results = {
            'CycleTimeCalculator': pd.DataFrame({'cycle_time': [1, 2, 3]}),
            'ThroughputCalculator': pd.DataFrame({'count': [5, 4, 6]}),
            'WIPChartCalculator': pd.DataFrame({'wip': [10, 12, 11]}),
            'CFDCalculator': pd.DataFrame({'stage1': [5, 6, 7], 'stage2': [3, 4, 5]}),
            'AgeingWIPChartCalculator': pd.DataFrame({'age': [1, 5, 10]})
        }
        
        generator = AIContextGenerator(mock_query_manager, test_settings, mock_results)
        
        raw_data = generator._collect_raw_data()
        
        assert 'cycle_time' in raw_data
        assert 'throughput' in raw_data
        assert 'wip' in raw_data
        assert 'cfd' in raw_data
        assert 'ageing_wip' in raw_data
        
        # Verify data integrity
        assert len(raw_data['cycle_time']) == 3
        assert len(raw_data['throughput']) == 3

    def test_collect_raw_data_missing_calculators(self, mock_query_manager, test_settings):
        """Test raw data collection when some calculators are missing."""
        # Only provide some calculator results
        mock_results = {
            'CycleTimeCalculator': pd.DataFrame({'cycle_time': [1, 2, 3]})
        }
        
        generator = AIContextGenerator(mock_query_manager, test_settings, mock_results)
        
        raw_data = generator._collect_raw_data()
        
        assert 'cycle_time' in raw_data
        assert len(raw_data) == 1  # Only one calculator had data

    def test_run_with_raw_data_collection(self, mock_query_manager, test_settings):
        """Test that run() method collects raw data for later AI analysis."""
        # Add copilot_context to settings to enable the generator
        test_settings['copilot_context'] = 'test-output.json'

        mock_cycle_data = pd.DataFrame({
            'key': ['PROJ-1', 'PROJ-2'],
            'cycle_time': [5, 8],
            'Done': [pd.Timestamp('2024-01-01'), pd.Timestamp('2024-01-02')]
        })

        mock_results = {
            'CycleTimeCalculator': mock_cycle_data,
            'AgeingWIPChartCalculator': pd.DataFrame({'age': [1, 5], 'key': ['PROJ-3', 'PROJ-4']}),
            'ThroughputCalculator': pd.DataFrame({'count': [2, 3, 1]}),
            'WIPChartCalculator': pd.DataFrame({'wip': [5, 6, 4]}),
            'CFDCalculator': pd.DataFrame({'stage1': [2, 3], 'stage2': [1, 2]})
        }

        generator = AIContextGenerator(mock_query_manager, test_settings, mock_results)

        result = generator.run()

        # Verify result is not None and contains expected data
        assert result is not None
        assert 'metadata' in result
        assert 'flow_health' in result
        assert 'ageing_wip_analysis' in result

        # Verify raw data is collected for later AI analysis
        assert 'raw_data' in result
        assert 'cycle_time' in result['raw_data']
        assert 'throughput' in result['raw_data']
        assert 'wip' in result['raw_data']
        assert 'cfd' in result['raw_data']
        assert 'ageing_wip' in result['raw_data']

    def test_run_without_copilot_context(self, mock_query_manager, test_settings):
        """Test that run() method returns None when copilot_context is not configured."""
        # Don't add copilot_context to settings - should return None
        mock_cycle_data = pd.DataFrame({
            'key': ['PROJ-1'],
            'cycle_time': [5],
            'Done': [pd.Timestamp('2024-01-01')]
        })

        mock_results = {'CycleTimeCalculator': mock_cycle_data}
        generator = AIContextGenerator(mock_query_manager, test_settings, mock_results)

        result = generator.run()

        # Should return None when copilot_context is not configured
        assert result is None
        assert generator.settings == test_settings

    def test_run_skips_when_no_output_configured(self, mock_query_manager, test_settings):
        """Test that run() returns None when no copilot context output is configured."""
        # Don't set copilot_context in settings
        mock_cycle_data = pd.DataFrame({
            'key': ['PROJ-1'],
            'cycle_time': [5],
            'Done': [pd.Timestamp('2024-01-01')]
        })
        
        mock_results = {'CycleTimeCalculator': mock_cycle_data}
        generator = AIContextGenerator(mock_query_manager, test_settings, mock_results)
        
        result = generator.run()
        
        # Verify that the generator skips execution and returns None
        assert result is None

    def test_run_generates_flow_context(self, mock_query_manager, test_settings, tmp_path):
        # Mock cycle time data in results to avoid "no data" error
        from jira_agile_metrics.calculators.cycletime import CycleTimeCalculator

        # Use tmp_path for the output file and enable copilot context
        output_file = tmp_path / "ai-context.json"
        test_settings["ai_context_file"] = str(output_file)
        test_settings["copilot_context"] = str(output_file)

        mock_cycle_data = pd.DataFrame([{"key": "PROJ-123", "cycle_time": 5.0}])

        generator = AIContextGenerator(
            mock_query_manager,
            test_settings,
            {CycleTimeCalculator: mock_cycle_data},
        )

        # Mock all the analysis methods
        with patch.object(generator, "_analyze_flow_health") as mock_flow_health, patch.object(
            generator, "_analyze_ageing_wip"
        ) as mock_ageing_wip, patch.object(generator, "_analyze_throughput_trends") as mock_throughput, patch.object(
            generator, "_analyze_wip_stability"
        ) as mock_wip_stability, patch.object(
            generator, "_detect_bottlenecks"
        ) as mock_bottlenecks, patch.object(
            generator, "_analyze_cycle_time_patterns"
        ) as mock_patterns, patch.object(
            generator, "_identify_actionable_items"
        ) as mock_actionable:

            # Set up mock returns
            mock_flow_health.return_value = {
                "avg_cycle_time": 9.0,
                "predictability_ratio": 1.25,
            }
            mock_ageing_wip.return_value = {
                "total_wip_items": 1,
                "stuck_items_count": 0,
            }
            mock_throughput.return_value = {
                "recent_avg_throughput": 2.0,
                "trend_direction": "stable",
            }
            mock_wip_stability.return_value = {
                "current_wip": 1,
                "wip_trend": "stable",
            }
            mock_bottlenecks.return_value = {"potential_bottlenecks": []}
            mock_patterns.return_value = {"issue_type_patterns": {}}
            mock_actionable.return_value = []

            result = generator.run()

        # Verify result is not None and has flow-focused structure
        assert result is not None
        assert "metadata" in result
        assert "flow_health" in result
        assert "ageing_wip_analysis" in result
        assert "throughput_trends" in result
        assert "wip_stability" in result
        assert "bottleneck_detection" in result
        assert "cycle_time_patterns" in result
        assert "actionable_items" in result

        # Verify metadata structure
        metadata = result["metadata"]
        assert "analysis_date" in metadata
        assert "workflow_stages" in metadata
        assert "committed_column" in metadata
        assert "done_column" in metadata
        assert "analysis_date" in metadata

    def test_analyze_flow_health_no_data(self, mock_query_manager, test_settings):
        generator = AIContextGenerator(mock_query_manager, test_settings, {})

        # Mock empty cycle data with proper columns
        empty_data = pd.DataFrame(columns=["cycle_time", "Done"])
        result = generator._analyze_flow_health(empty_data)

        # Should handle no cycle data gracefully
        assert result["status"] == "no_data"

    def test_analyze_ageing_wip_no_items(self, mock_query_manager, test_settings):
        generator = AIContextGenerator(mock_query_manager, test_settings, {})

        with patch("jira_agile_metrics.calculators.ageingwip.AgeingWIPChartCalculator") as mock_calc:
            mock_calc.return_value.run.return_value = None

            result = generator._analyze_ageing_wip()

        assert result["status"] == "no_wip_items"

    def test_analyze_ageing_wip_with_stuck_items(self, mock_query_manager, test_settings):
        # Mock ageing WIP data with required 'status' column
        # Average age = (130 + 5*7) / 8 = 165/8 = 20.625, so stuck threshold = 41.25
        # Age 130 > 41.25, so PROJ-123 should be stuck
        mock_ageing_data = pd.DataFrame(
            [
                {
                    "key": "PROJ-123",
                    "summary": "Old item",
                    "age": 130,
                    "status": "In Progress",
                },
                {
                    "key": "PROJ-456",
                    "summary": "Recent item",
                    "age": 5,
                    "status": "In Progress",
                },
                {
                    "key": "PROJ-457",
                    "summary": "Recent item",
                    "age": 5,
                    "status": "In Progress",
                },
                {
                    "key": "PROJ-458",
                    "summary": "Recent item",
                    "age": 5,
                    "status": "In Progress",
                },
                {
                    "key": "PROJ-459",
                    "summary": "Recent item",
                    "age": 5,
                    "status": "In Progress",
                },
                {
                    "key": "PROJ-460",
                    "summary": "Recent item",
                    "age": 5,
                    "status": "In Progress",
                },
                {
                    "key": "PROJ-461",
                    "summary": "Recent item",
                    "age": 5,
                    "status": "In Progress",
                },
                {
                    "key": "PROJ-462",
                    "summary": "Recent item",
                    "age": 5,
                    "status": "In Progress",
                },
            ]
        )

        # Create generator with pre-populated results
        from jira_agile_metrics.calculators.ageingwip import AgeingWIPChartCalculator
        results = {AgeingWIPChartCalculator: mock_ageing_data}
        generator = AIContextGenerator(mock_query_manager, test_settings, results)

        result = generator._analyze_ageing_wip()

        assert result["total_wip_items"] == 8
        assert result["stuck_items_count"] == 1  # PROJ-123 with age 130 > threshold ~41
        assert len(result["stuck_items"]) == 1
        assert result["stuck_items"][0]["key"] == "PROJ-123"

    def test_analyze_throughput_trends_no_data(self, mock_query_manager, test_settings):
        generator = AIContextGenerator(mock_query_manager, test_settings, {})

        with patch("jira_agile_metrics.calculators.throughput.ThroughputCalculator") as mock_calc:
            mock_calc.return_value.run.return_value = None

            result = generator._analyze_throughput_trends()

        assert result["status"] == "no_throughput_data"

    def test_analyze_throughput_trends_with_data(self, mock_query_manager, test_settings):
        # Mock throughput data - improving trend
        mock_throughput_data = pd.DataFrame(
            [
                {"period": "2025-W30", "count": 1.0},
                {"period": "2025-W31", "count": 2.0},
                {"period": "2025-W32", "count": 3.0},
                {"period": "2025-W33", "count": 2.5},
            ]
        )

        # Create generator with pre-populated results
        from jira_agile_metrics.calculators.throughput import ThroughputCalculator
        results = {ThroughputCalculator: mock_throughput_data}
        generator = AIContextGenerator(mock_query_manager, test_settings, results)

        result = generator._analyze_throughput_trends()

        assert result["recent_avg_throughput"] == 2.125  # avg of all periods (actual implementation)
        assert result["historical_avg_throughput"] == 2.125  # avg of all periods
        assert result["trend_direction"] == "stable"  # Based on actual implementation logic
        assert result["min_throughput"] == 1.0
        assert result["max_throughput"] == 3.0

    def test_detect_bottlenecks_no_data(self, mock_query_manager, test_settings):
        generator = AIContextGenerator(mock_query_manager, test_settings, {})

        with patch("jira_agile_metrics.calculators.cfd.CFDCalculator") as mock_calc:
            mock_calc.return_value.run.return_value = None

            result = generator._detect_bottlenecks()

        assert result["status"] == "no_cfd_data"

    def test_identify_actionable_items_no_wip(self, mock_query_manager, test_settings):
        generator = AIContextGenerator(mock_query_manager, test_settings, {})

        # Empty cycle data
        empty_data = pd.DataFrame(columns=["key", "summary", "In Progress", "Done"])

        result = generator._identify_actionable_items(empty_data)

        assert result == []

    def test_identify_actionable_items_with_outliers(self, mock_query_manager, test_settings):
        generator = AIContextGenerator(mock_query_manager, test_settings, {})

        # Mock cycle data with WIP items and completed items for threshold calculation
        cycle_data = pd.DataFrame(
            [
                # WIP items
                {
                    "key": "PROJ-123",
                    "summary": "Old WIP item",
                    "In Progress": pd.Timestamp("2025-08-01"),
                    "Done": pd.NaT,
                    "cycle_time": None,
                },
                {
                    "key": "PROJ-456",
                    "summary": "Recent WIP item",
                    "In Progress": pd.Timestamp("2025-08-25"),
                    "Done": pd.NaT,
                    "cycle_time": None,
                },
                # Completed items for threshold
                {
                    "key": "PROJ-789",
                    "summary": "Completed",
                    "In Progress": pd.Timestamp("2025-08-15"),
                    "Done": pd.Timestamp("2025-08-20"),
                    "cycle_time": 5.0,
                },
                {
                    "key": "PROJ-101",
                    "summary": "Completed",
                    "In Progress": pd.Timestamp("2025-08-10"),
                    "Done": pd.Timestamp("2025-08-18"),
                    "cycle_time": 8.0,
                },
            ]
        )

        with patch("pandas.Timestamp.now") as mock_now:
            mock_now.return_value = pd.Timestamp("2025-08-29")

            result = generator._identify_actionable_items(cycle_data)

        # Should identify the old WIP item as actionable (28 days > 85th percentile of [5, 8])
        assert len(result) > 0
        assert result[0]["key"] == "PROJ-123"
        assert result[0]["reason"] == "ageing_outlier"
        assert result[0]["age_days"] == 28

    def test_analysis_with_timedelta_cycle_time(self, mock_query_manager, test_settings):
        """Test that analysis functions handle Timedelta cycle times correctly."""
        generator = AIContextGenerator(mock_query_manager, test_settings, {})

        # Mock cycle data with Timedelta objects
        cycle_data = pd.DataFrame(
            [
                {
                    "key": "PROJ-1",
                    "In Progress": pd.Timestamp("2025-08-01"),
                    "Done": pd.Timestamp("2025-08-06"),
                    "cycle_time": pd.Timedelta(days=5),
                },
                {
                    "key": "PROJ-2",
                    "In Progress": pd.Timestamp("2025-08-10"),
                    "Done": pd.Timestamp("2025-08-20"),
                    "cycle_time": pd.Timedelta(days=10),
                },
                {
                    "key": "PROJ-3",
                    "In Progress": pd.Timestamp("2025-08-25"),
                    "Done": pd.NaT,  # WIP
                    "cycle_time": None,
                },
            ]
        )

        # 1. Test _analyze_flow_health
        health_result = generator._analyze_flow_health(cycle_data)
        assert health_result["avg_cycle_time"] == 7.5
        assert health_result["median_cycle_time"] == 7.5
        assert isinstance(health_result["avg_cycle_time"], float)

        # 2. Test _analyze_cycle_time_patterns (with enough data)
        cycle_data_for_patterns = pd.DataFrame(
            [{"cycle_time": pd.Timedelta(days=d), "Done": pd.Timestamp.now()} for d in range(1, 12)]
        )
        patterns_result = generator._analyze_cycle_time_patterns(cycle_data_for_patterns)
        assert "performance_trend" in patterns_result
        assert isinstance(patterns_result["performance_trend"]["recent_avg_cycle_time"], float)

        # 3. Test _identify_actionable_items
        with patch("pandas.Timestamp.now") as mock_now:
            mock_now.return_value = pd.Timestamp("2025-08-30")
            actionable_result = generator._identify_actionable_items(cycle_data)

        # PROJ-3 is 5 days old. 85th percentile of [5, 10] is 9.25. So not an outlier.
        # Let's make it an outlier
        cycle_data.loc[cycle_data["key"] == "PROJ-3", "In Progress"] = pd.Timestamp("2025-08-15")

        with patch("pandas.Timestamp.now") as mock_now:
            mock_now.return_value = pd.Timestamp("2025-08-30")
            actionable_result = generator._identify_actionable_items(cycle_data)

        assert len(actionable_result) == 1
        assert actionable_result[0]["key"] == "PROJ-3"
        assert actionable_result[0]["age_days"] == 15
        assert actionable_result[0]["threshold_exceeded"] > 8.0
