"""
Tests for PatternAnalyzer - Enhanced AI pattern detection functionality.
"""

import json
import pytest
from unittest.mock import Mock, patch
import pandas as pd

from .pattern_analyzer import PatternAnalyzer
from .providers import LLMProvider


class MockLLMProvider(LLMProvider):
    """Mock LLM provider for testing."""
    
    def __init__(self, response="{}"):
        self.response = response
        self.last_prompt = None
        self.last_context = None
        self.call_count = 0
        self.responses = []
        self.response_index = 0
    
    def generate_insights(self, prompt, context, dry_run=False):
        self.last_prompt = prompt
        self.last_context = context
        self.call_count += 1
        
        if dry_run:
            return "Dry run response"
        
        return self.response
    
    def validate_config(self) -> bool:
        return True


class TestPatternAnalyzer:
    """Test PatternAnalyzer functionality."""
    
    def test_actionable_recommendations_format(self):
        """Test that actionable recommendations are properly formatted."""
        mock_response = json.dumps({
            "recommendations": [
                {
                    "issue": "High WIP causing delays",
                    "action": "Implement WIP limits of 5 items per developer",
                    "owner": "Scrum Master",
                    "timeline": "1 week to implement, 2 sprints to see results",
                    "success_metric": "Reduce cycle time by 30%",
                    "evidence": "Average WIP is 12 items, 85th percentile cycle time is 15 days",
                    "priority": "high",
                    "effort": "low"
                }
            ]
        })
        
        mock_llm = MockLLMProvider(mock_response)
        analyzer = PatternAnalyzer(mock_llm, "enhanced")
        
        raw_data = {"cycle_time": pd.DataFrame({"key": ["A-1"], "cycle_time": [10]})}
        imperative_insights = {"flow_health": {"wip_average": 12}}
        
        result = analyzer._analyze_flow_anomalies(raw_data, imperative_insights, dry_run=False)
        
        assert "patterns" in result
        assert len(result["patterns"]) == 1
        
        pattern = result["patterns"][0]
        assert pattern["type"] == "actionable_recommendation"
        assert pattern["description"] == "High WIP causing delays"
        assert pattern["action"] == "Implement WIP limits of 5 items per developer"
        assert pattern["owner"] == "Scrum Master"
        assert pattern["timeline"] == "1 week to implement, 2 sprints to see results"
        assert pattern["success_metric"] == "Reduce cycle time by 30%"
        assert pattern["priority"] == "high"
        assert pattern["effort"] == "low"
    
    def test_no_story_points_in_recommendations(self):
        """Test that story points are never mentioned in AI recommendations."""
        # Mock response that would contain story points - should not happen in practice
        mock_response = json.dumps({
            "recommendations": [
                {
                    "issue": "Cycle time variance too high",
                    "action": "Break down large work items into smaller tasks",
                    "owner": "Product Owner",
                    "timeline": "2 weeks to implement new breakdown process",
                    "success_metric": "Reduce cycle time variance by 25%",
                    "evidence": "85th percentile is 3x median cycle time",
                    "priority": "medium",
                    "effort": "medium"
                }
            ]
        })
        
        mock_llm = MockLLMProvider(mock_response)
        analyzer = PatternAnalyzer(mock_llm, "enhanced")
        
        raw_data = {"cycle_time": pd.DataFrame({"key": ["A-1"], "cycle_time": [10]})}
        imperative_insights = {"cycle_time_patterns": {"variance_high": True}}
        
        result = analyzer._analyze_flow_anomalies(raw_data, imperative_insights, dry_run=False)
        
        # Verify no story points mentioned in any field
        for pattern in result.get("patterns", []):
            for field_value in pattern.values():
                if isinstance(field_value, str):
                    assert "story point" not in field_value.lower()
                    assert "story points" not in field_value.lower()
                    assert "point estimate" not in field_value.lower()
        
        # Also check the prompt sent to LLM doesn't mention story points
        prompt = mock_llm.last_prompt or ""
        assert "story point" not in prompt.lower()
        assert "story points" not in prompt.lower()

    def test_recommendation_categories(self):
        """Test that recommendations include proper categorization."""
        mock_response = json.dumps({
            "recommendations": [
                {
                    "issue": "High WIP causing delays",
                    "action": "Implement WIP limits",
                    "owner": "Scrum Master",
                    "timeline": "1 week",
                    "success_metric": "Reduce cycle time by 20%",
                    "evidence": "WIP at 15 items",
                    "priority": "high",
                    "effort": "low",
                    "category": "quick_wins"
                },
                {
                    "issue": "Process inefficiencies",
                    "action": "Redesign workflow stages",
                    "owner": "Team Lead",
                    "timeline": "3 months",
                    "success_metric": "Improve flow efficiency by 40%",
                    "evidence": "Multiple bottlenecks detected",
                    "priority": "medium",
                    "effort": "high",
                    "category": "foundational"
                }
            ]
        })
        
        mock_llm = MockLLMProvider(mock_response)
        analyzer = PatternAnalyzer(mock_llm, "basic")
        
        raw_data = {"wip": pd.DataFrame({"count": [15, 14, 16]})}
        imperative_insights = {"flow_health": {"wip_high": True}}
        
        result = analyzer.analyze_flow_patterns(raw_data, imperative_insights)
        
        assert "patterns" in result
        assert len(result["patterns"]) == 2
        
        # Check first recommendation (quick win)
        quick_win = result["patterns"][0]
        assert quick_win["category"] == "quick_wins"
        assert quick_win["priority"] == "high"
        assert quick_win["effort"] == "low"
        assert quick_win["type"] == "basic_recommendation"
        
        # Check second recommendation (foundational)
        foundational = result["patterns"][1]
        assert foundational["category"] == "foundational"
        assert foundational["priority"] == "medium"
        assert foundational["effort"] == "high"
        assert foundational["type"] == "basic_recommendation"

    def test_cross_correlations_actionable_format(self):
        """Test that cross-correlation analysis provides actionable recommendations."""
        mock_response = json.dumps({
            "recommendations": [
                {
                    "issue": "WIP increases but throughput stays flat",
                    "action": "Identify and remove capacity constraints in bottleneck stages",
                    "owner": "Engineering Manager",
                    "timeline": "2 weeks to analyze, 1 month to implement fixes",
                    "success_metric": "Throughput increases proportionally with WIP",
                    "evidence": "WIP up 30% but throughput unchanged over 4 weeks",
                    "priority": "high",
                    "effort": "medium",
                    "category": "strategic"
                }
            ]
        })
        
        mock_llm = MockLLMProvider(mock_response)
        analyzer = PatternAnalyzer(mock_llm, "enhanced")
        
        raw_data = {
            "wip": pd.DataFrame({"count": [10, 12, 13]}),
            "throughput": pd.DataFrame({"count": [5, 5, 5]})
        }
        imperative_insights = {"correlations": {"wip_throughput_decoupled": True}}
        
        result = analyzer._analyze_cross_correlations(raw_data, imperative_insights, dry_run=False)
        
        assert "patterns" in result
        assert len(result["patterns"]) == 1
        
        correlation_rec = result["patterns"][0]
        assert correlation_rec["type"] == "correlation_recommendation"
        assert correlation_rec["category"] == "strategic"
        assert correlation_rec["action"] == "Identify and remove capacity constraints in bottleneck stages"
        assert correlation_rec["owner"] == "Engineering Manager"
        assert "WIP increases but throughput stays flat" in correlation_rec["description"]

    def test_init_basic_depth(self):
        """Test PatternAnalyzer initialization with basic depth."""
        mock_llm = MockLLMProvider()
        analyzer = PatternAnalyzer(mock_llm, "basic")
        
        assert analyzer.llm == mock_llm
        assert analyzer.analysis_depth == "basic"

    def test_init_enhanced_depth(self):
        """Test PatternAnalyzer initialization with enhanced depth."""
        mock_llm = MockLLMProvider()
        analyzer = PatternAnalyzer(mock_llm, "enhanced")
        
        assert analyzer.analysis_depth == "enhanced"

    def test_analyze_flow_patterns_basic_success(self):
        """Test basic pattern analysis with successful response."""
        mock_response = json.dumps({
            "recommendations": [
                {
                    "issue": "Throughput declining while WIP stable",
                    "action": "Implement daily throughput tracking and WIP limits",
                    "owner": "Scrum Master",
                    "timeline": "2 weeks to implement, 1 month to see results",
                    "success_metric": "Increase throughput by 20%",
                    "evidence": "Last 4 weeks show 20% throughput drop",
                    "priority": "high",
                    "effort": "medium",
                    "category": "quick_wins"
                }
            ]
        })
        
        mock_llm = MockLLMProvider(mock_response)
        analyzer = PatternAnalyzer(mock_llm, "basic")
        
        raw_data = {"throughput": pd.DataFrame({"count": [5, 4, 3, 3]})}
        imperative_insights = {"flow_health": {"status": "declining"}}
        
        result = analyzer.analyze_flow_patterns(raw_data, imperative_insights)
        
        assert "patterns" in result
        assert len(result["patterns"]) == 1
        assert result["patterns"][0]["type"] == "basic_recommendation"
        assert result["patterns"][0]["category"] == "quick_wins"
        assert result["patterns"][0]["action"] == "Implement daily throughput tracking and WIP limits"
        assert mock_llm.call_count == 1

    def test_analyze_flow_patterns_basic_dry_run(self, capsys):
        """Test basic pattern analysis in dry run mode."""
        mock_llm = MockLLMProvider()
        analyzer = PatternAnalyzer(mock_llm, "basic")
        
        raw_data = {"throughput": pd.DataFrame({"count": [5, 4, 3]})}
        imperative_insights = {"flow_health": {"status": "declining"}}
        
        result = analyzer.analyze_flow_patterns(raw_data, imperative_insights, dry_run=True)
        
        assert "recommendations" in result
        assert result["recommendations"] == []
        assert mock_llm.call_count == 0  # No API calls in dry run
        
        # Verify prompt was displayed
        captured = capsys.readouterr()
        assert "PATTERN ANALYZER - BASIC ANALYSIS (DRY RUN)" in captured.out
        assert "PROMPT:" in captured.out
        assert "RAW DATA SUMMARY:" in captured.out

    def test_analyze_flow_patterns_enhanced_success(self):
        """Test enhanced pattern analysis with multiple specialized analyses."""
        # Mock responses for different analysis types
        flow_response = json.dumps({
            "patterns": [{"type": "flow_anomaly", "description": "Flow issue", "confidence": 0.7}]
        })
        temporal_response = json.dumps({
            "patterns": [{"type": "temporal_pattern", "description": "Weekly cycle", "confidence": 0.6}]
        })
        correlation_response = json.dumps({
            "patterns": [{"type": "cross_correlation", "description": "WIP-throughput inverse", "confidence": 0.9}]
        })
        
        mock_llm = MockLLMProvider()
        # Simulate different responses for different calls
        mock_llm.responses = [flow_response, temporal_response, correlation_response]
        mock_llm.response_index = 0
        
        def mock_generate_insights(prompt, context, dry_run=False):
            mock_llm.call_count += 1
            if mock_llm.response_index < len(mock_llm.responses):
                response = mock_llm.responses[mock_llm.response_index]
                mock_llm.response_index += 1
                return response
            return "{}"
        
        mock_llm.generate_insights = mock_generate_insights
        
        analyzer = PatternAnalyzer(mock_llm, "enhanced")
        
        raw_data = {
            "throughput": pd.DataFrame({"count": [5, 4, 3, 3]}),
            "wip": pd.DataFrame({"wip": [10, 12, 12, 13]})
        }
        imperative_insights = {"flow_health": {"status": "declining"}}
        
        result = analyzer.analyze_flow_patterns(raw_data, imperative_insights)
        
        assert result["status"] == "success"
        assert result["analysis_depth"] == "enhanced"
        assert len(result["patterns"]) == 3  # One from each analysis type
        assert mock_llm.call_count == 3

    def test_analyze_flow_patterns_experimental_filtering(self):
        """Test experimental mode filters low-confidence patterns."""
        mock_response = json.dumps({
            "patterns": [
                {"type": "pattern1", "confidence": 0.9, "description": "High confidence"},
                {"type": "pattern2", "confidence": 0.7, "description": "Medium confidence"},
                {"type": "pattern3", "confidence": 0.5, "description": "Low confidence"}
            ]
        })
        
        mock_llm = MockLLMProvider(mock_response)
        analyzer = PatternAnalyzer(mock_llm, "experimental")
        
        result = analyzer.analyze_flow_patterns({}, {})
        
        # Experimental mode should filter out patterns with confidence <= 0.8
        assert result["analysis_depth"] == "experimental"
        # Since the enhanced analysis calls 3 sub-analyses, each returning the same pattern,
        # we should have 3 high-confidence patterns after filtering
        high_confidence_patterns = [p for p in result["patterns"] if p.get("confidence", 0) > 0.8]
        assert len(high_confidence_patterns) >= 1
        assert all(p["confidence"] > 0.8 for p in high_confidence_patterns)

    def test_analyze_flow_anomalies_success(self):
        """Test flow anomaly detection."""
        mock_response = json.dumps({
            "patterns": [
                {
                    "type": "flow_anomaly",
                    "description": "Unusual throughput pattern",
                    "evidence": "Throughput dropped 30% without WIP change",
                    "confidence": 0.8,
                    "impact": "high",
                    "investigation": "Check for quality issues"
                }
            ]
        })
        
        mock_llm = MockLLMProvider(mock_response)
        analyzer = PatternAnalyzer(mock_llm, "enhanced")
        
        raw_data = {"throughput": pd.DataFrame({"count": [10, 7, 7, 6]})}
        result = analyzer._analyze_flow_anomalies(raw_data, {}, dry_run=False)
        
        assert len(result["patterns"]) == 1
        assert result["patterns"][0]["type"] == "flow_anomaly"
        assert "throughput dropped" in result["patterns"][0]["evidence"].lower()

    def test_analyze_temporal_patterns_success(self):
        """Test temporal pattern detection."""
        mock_response = json.dumps({
            "patterns": [
                {
                    "type": "temporal_pattern",
                    "description": "Weekly performance cycle",
                    "evidence": "Throughput consistently lower on Mondays",
                    "confidence": 0.7,
                    "impact": "low",
                    "recommendation": "Investigate Monday standup effectiveness"
                }
            ]
        })
        
        mock_llm = MockLLMProvider(mock_response)
        analyzer = PatternAnalyzer(mock_llm, "enhanced")
        
        # Create time-series data that might show weekly patterns
        dates = pd.date_range('2024-01-01', periods=14, freq='D')
        raw_data = {
            "throughput": pd.DataFrame({
                "date": dates,
                "count": [3, 5, 6, 7, 8, 4, 2, 3, 5, 6, 7, 8, 4, 2]  # Weekly pattern
            })
        }
        
        result = analyzer._analyze_temporal_patterns(raw_data, {}, dry_run=False)
        
        assert len(result["patterns"]) == 1
        assert result["patterns"][0]["type"] == "temporal_pattern"
        assert "weekly" in result["patterns"][0]["description"].lower()

    def test_analyze_cross_correlations_success(self):
        """Test cross-metric correlation detection."""
        mock_response = json.dumps({
            "patterns": [
                {
                    "type": "cross_correlation",
                    "description": "Inverse WIP-throughput relationship",
                    "evidence": "As WIP increased 20%, throughput decreased 15%",
                    "confidence": 0.85,
                    "impact": "high",
                    "hypothesis": "Team hitting capacity constraints"
                }
            ]
        })
        
        mock_llm = MockLLMProvider(mock_response)
        analyzer = PatternAnalyzer(mock_llm, "enhanced")
        
        raw_data = {
            "wip": pd.DataFrame({"wip": [10, 12, 14, 16]}),
            "throughput": pd.DataFrame({"count": [8, 7, 6, 5]})
        }
        
        result = analyzer._analyze_cross_correlations(raw_data, {}, dry_run=False)
        
        assert len(result["patterns"]) == 1
        assert result["patterns"][0]["type"] == "cross_correlation"
        assert "inverse" in result["patterns"][0]["description"].lower()

    def test_format_time_series_data(self):
        """Test time-series data formatting for AI analysis."""
        mock_llm = MockLLMProvider()
        analyzer = PatternAnalyzer(mock_llm, "basic")
        
        raw_data = {
            "throughput": pd.DataFrame({"count": [5, 4, 3]}),
            "wip": pd.DataFrame({"wip": [10, 12, 11]})
        }
        
        formatted = analyzer._format_time_series_data(raw_data)
        
        assert "THROUGHPUT:" in formatted
        assert "WIP:" in formatted
        assert "5" in formatted  # Check data is included

    def test_format_time_series_data_empty(self):
        """Test time-series data formatting with empty data."""
        mock_llm = MockLLMProvider()
        analyzer = PatternAnalyzer(mock_llm, "basic")
        
        formatted = analyzer._format_time_series_data({})
        
        assert formatted == "No time-series data available"

    def test_parse_json_response_success(self):
        """Test successful JSON response parsing."""
        mock_llm = MockLLMProvider()
        analyzer = PatternAnalyzer(mock_llm, "basic")
        
        json_response = json.dumps({
            "patterns": [
                {"type": "test", "description": "Test pattern", "confidence": 0.8}
            ]
        })
        
        result = analyzer._parse_json_response(json_response)
        
        assert len(result["patterns"]) == 1
        assert result["patterns"][0]["type"] == "test"

    def test_parse_json_response_with_markdown(self):
        """Test JSON response parsing with markdown code blocks."""
        mock_llm = MockLLMProvider()
        analyzer = PatternAnalyzer(mock_llm, "basic")
        
        markdown_response = """```json
{
  "patterns": [
    {"type": "test", "description": "Test pattern", "confidence": 0.7}
  ]
}
```"""
        
        result = analyzer._parse_json_response(markdown_response)
        
        assert len(result["patterns"]) == 1
        assert result["patterns"][0]["type"] == "test"

    def test_parse_json_response_invalid_json(self):
        """Test JSON response parsing with invalid JSON."""
        mock_llm = MockLLMProvider()
        analyzer = PatternAnalyzer(mock_llm, "basic")
        
        invalid_response = "This is not valid JSON"
        
        result = analyzer._parse_json_response(invalid_response)
        
        assert result["patterns"] == []

    def test_parse_pattern_response_text_fallback(self):
        """Test pattern response parsing falls back to text parsing."""
        mock_llm = MockLLMProvider()
        analyzer = PatternAnalyzer(mock_llm, "basic")
        
        text_response = """
Pattern: Unusual throughput decline
- Evidence: 30% drop in last week
- Impact: High

Anomaly: WIP accumulation in Code Review
- Evidence: 5 items stuck for >7 days
"""
        
        result = analyzer._parse_pattern_response(text_response)
        
        assert result["status"] == "success"
        assert len(result["patterns"]) == 2
        assert "Pattern:" in result["patterns"][0]["description"]
        assert "Anomaly:" in result["patterns"][1]["description"]

    def test_error_handling_llm_failure(self):
        """Test error handling when LLM calls fail."""
        mock_llm = Mock()
        mock_llm.generate_insights.side_effect = Exception("API Error")
        
        analyzer = PatternAnalyzer(mock_llm, "basic")
        
        result = analyzer.analyze_flow_patterns({}, {})
        
        assert result["status"] == "error"
        assert "API Error" in result["message"]

    def test_analysis_depth_configuration(self):
        """Test different analysis depth configurations."""
        mock_llm = MockLLMProvider('{"patterns": []}')
        
        # Test all depth levels
        for depth in ["basic", "enhanced", "experimental"]:
            analyzer = PatternAnalyzer(mock_llm, depth)
            result = analyzer.analyze_flow_patterns({}, {})
            
            if depth == "enhanced":
                assert result.get("analysis_depth") == "enhanced"
            elif depth == "experimental":
                assert result.get("analysis_depth") == "experimental"
            else:
                # Basic analysis returns patterns
                assert "patterns" in result
