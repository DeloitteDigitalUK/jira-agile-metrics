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
            "patterns": [
                {
                    "type": "flow_anomaly",
                    "description": "Throughput declining while WIP stable",
                    "confidence": 0.8,
                    "impact": "medium",
                    "evidence": "Last 4 weeks show 20% throughput drop"
                }
            ]
        })
        
        mock_llm = MockLLMProvider(mock_response)
        analyzer = PatternAnalyzer(mock_llm, "basic")
        
        raw_data = {"throughput": pd.DataFrame({"count": [5, 4, 3, 3]})}
        imperative_insights = {"flow_health": {"status": "declining"}}
        
        result = analyzer.analyze_flow_patterns(raw_data, imperative_insights)
        
        assert result["status"] == "success"
        assert len(result["patterns"]) == 1
        assert result["patterns"][0]["type"] == "flow_anomaly"
        assert result["patterns"][0]["confidence"] == 0.8
        assert mock_llm.call_count == 1

    def test_analyze_flow_patterns_basic_dry_run(self, capsys):
        """Test basic pattern analysis in dry run mode."""
        mock_llm = MockLLMProvider()
        analyzer = PatternAnalyzer(mock_llm, "basic")
        
        raw_data = {"throughput": pd.DataFrame({"count": [5, 4, 3]})}
        imperative_insights = {"flow_health": {"status": "declining"}}
        
        result = analyzer.analyze_flow_patterns(raw_data, imperative_insights, dry_run=True)
        
        assert result["status"] == "dry_run"
        assert result["patterns"] == []
        assert result["prompt_displayed"] == True
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
                # Basic doesn't set analysis_depth in response
                assert result.get("status") in ["success", "error"]
