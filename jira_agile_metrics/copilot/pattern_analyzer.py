"""
Enhanced AI pattern detection for agile metrics analysis.
Uses sophisticated prompting to identify patterns that imperative analysis might miss.
"""

import json
import logging
from typing import Dict, List, Optional
import pandas as pd
from .providers import LLMProvider

logger = logging.getLogger(__name__)


class PatternAnalyzer:
    """AI-powered pattern detection for flow metrics."""

    def __init__(self, llm_provider: Optional[LLMProvider], analysis_depth: str = "basic"):
        self.llm = llm_provider
        self.analysis_depth = analysis_depth  # basic, enhanced, experimental
        
    def analyze_flow_patterns(self, raw_data: Dict, imperative_insights: Dict, dry_run: bool = False) -> Dict:
        """
        Analyze flow patterns using AI to detect subtle issues missed by imperative analysis.
        
        Args:
            raw_data: Raw calculator results (cycle time, throughput, etc.)
            imperative_insights: Results from current AIContextGenerator
            dry_run: If True, don't call LLM API
            
        Returns:
            Dict with AI-detected patterns and confidence scores
        """
        if self.analysis_depth == "basic":
            return self._basic_pattern_analysis(raw_data, imperative_insights, dry_run)
        elif self.analysis_depth == "enhanced":
            return self._enhanced_pattern_analysis(raw_data, imperative_insights, dry_run)
        else:  # experimental
            return self._experimental_pattern_analysis(raw_data, imperative_insights, dry_run)
    
    def _basic_pattern_analysis(self, raw_data: Dict, imperative_insights: Dict, dry_run: bool) -> Dict:
        """Basic AI pattern detection - single focused prompt."""
        prompt = self._build_basic_pattern_prompt(raw_data, imperative_insights)
        
        try:
            if dry_run:
                print("\n" + "="*80)
                print("🔍 PATTERN ANALYZER - BASIC ANALYSIS (DRY RUN)")
                print("="*80)
                print("PROMPT:")
                print("-" * 40)
                print(prompt)
                print("-" * 40)
                print("RAW DATA SUMMARY:")
                print(f"Available datasets: {list(raw_data.keys())}")
                for key, data in raw_data.items():
                    if hasattr(data, 'shape'):
                        print(f"  {key}: {data.shape[0]} rows, {data.shape[1]} columns")
                    else:
                        print(f"  {key}: {type(data)}")
                print("="*80)
                return {"status": "dry_run", "patterns": [], "confidence": 0.0, "prompt_displayed": True}
                
            if not self.llm:
                return {"status": "dry_run", "patterns": [], "confidence": 0.0, "prompt_displayed": True}
            response = self.llm.generate_insights(prompt, raw_data, dry_run)
            return self._parse_pattern_response(response, confidence_base=0.7)
            
        except Exception as e:
            logger.warning(f"Basic pattern analysis failed: {e}")
            return {"status": "error", "message": str(e), "patterns": []}
    
    def _enhanced_pattern_analysis(self, raw_data: Dict, imperative_insights: Dict, dry_run: bool) -> Dict:
        """Enhanced AI pattern detection - multiple specialized prompts."""
        patterns = []
        
        if dry_run:
            print("\n" + "="*80)
            print("🔍 PATTERN ANALYZER - ENHANCED ANALYSIS (DRY RUN)")
            print("="*80)
            print("Enhanced mode runs 3 specialized analyses:")
            print("1. Flow Anomalies Detection")
            print("2. Temporal Patterns Analysis") 
            print("3. Cross-Metric Correlations")
            print("="*80)
        
        # Analyze different aspects separately for better focus
        analyses = [
            ("flow_anomalies", self._analyze_flow_anomalies),
            ("temporal_patterns", self._analyze_temporal_patterns),
            ("cross_metric_correlations", self._analyze_cross_correlations),
        ]
        
        for analysis_name, analysis_func in analyses:
            try:
                result = analysis_func(raw_data, imperative_insights, dry_run)
                if result.get("patterns"):
                    patterns.extend(result["patterns"])
            except Exception as e:
                logger.warning(f"Enhanced analysis {analysis_name} failed: {e}")
        
        return {
            "status": "success",
            "analysis_depth": "enhanced",
            "patterns": patterns,
            "total_patterns": len(patterns)
        }
    
    def _experimental_pattern_analysis(self, raw_data: Dict, imperative_insights: Dict, dry_run: bool) -> Dict:
        """Experimental pattern detection - advanced techniques."""
        # For now, same as enhanced but with different confidence scoring
        result = self._enhanced_pattern_analysis(raw_data, imperative_insights, dry_run)
        result["analysis_depth"] = "experimental"
        
        # Apply more aggressive pattern filtering for experimental mode
        if result.get("patterns"):
            filtered_patterns = [p for p in result["patterns"] if p.get("confidence", 0) > 0.8]
            result["patterns"] = filtered_patterns
            result["total_patterns"] = len(filtered_patterns)
        
        return result
    
    def _analyze_flow_anomalies(self, raw_data: Dict, imperative_insights: Dict, dry_run: bool) -> Dict:
        """Detect flow anomalies that don't match typical patterns."""
        prompt = f"""You are an expert in flow metrics analysis. Examine this team's data for SUBTLE ANOMALIES that might not be obvious:

CURRENT IMPERATIVE ANALYSIS FOUND:
{json.dumps(imperative_insights, indent=2, default=str)}

RAW TIME-SERIES DATA:
{self._format_time_series_data(raw_data)}

Look for these SUBTLE PATTERNS that imperative analysis might miss:

1. **Unusual Correlations**: Does throughput drop when WIP is stable? Does cycle time spike without obvious bottlenecks?

2. **Temporal Anomalies**: Are there recurring patterns by day of week, time of month, or seasonal trends?

3. **Leading Indicators**: Do you see early warning signs of problems that haven't fully manifested yet?

4. **Hidden Bottlenecks**: Are there constraints that don't show up in traditional CFD analysis?

5. **Quality Signals**: Do patterns suggest hidden quality issues affecting flow?

CRITICAL: Only identify patterns you can CLEARLY see in the data. Include:
- Specific evidence from the data
- Confidence level (0.0-1.0)
- Potential impact (low/medium/high)
- Recommended investigation steps

Format as JSON:
{{
  "patterns": [
    {{
      "type": "flow_anomaly",
      "description": "Brief description",
      "evidence": "Specific data points that support this",
      "confidence": 0.8,
      "impact": "medium",
      "investigation": "What the team should look into"
    }}
  ]
}}"""

        try:
            if dry_run:
                print("\n" + "="*80)
                print(" PATTERN ANALYZER - FLOW ANOMALIES (DRY RUN)")
                print("="*80)
                print("PROMPT:")
                print("-" * 40)
                print(prompt)
                print("-" * 40)
                print("RAW DATA SUMMARY:")
                print(f"Available datasets: {list(raw_data.keys())}")
                for key, data in raw_data.items():
                    if hasattr(data, 'shape'):
                        print(f"  {key}: {data.shape[0]} rows, {data.shape[1]} columns")
                    else:
                        print(f"  {key}: {type(data)}")
                print("="*80)
                return {"patterns": []}
            
            if not self.llm:
                return {"patterns": []}
            response = self.llm.generate_insights(prompt, raw_data, dry_run)
            return self._parse_json_response(response)
        except Exception as e:
            logger.warning(f"Flow anomaly analysis failed: {e}")
            return {"patterns": []}
    
    def _analyze_temporal_patterns(self, raw_data: Dict, imperative_insights: Dict, dry_run: bool) -> Dict:
        """Analyze temporal patterns and trends."""
        prompt = f"""Analyze TEMPORAL PATTERNS in this agile team's flow data:

TIME-SERIES DATA:
{self._format_time_series_data(raw_data)}

Look for these TEMPORAL PATTERNS:

1. **Cyclical Patterns**: Weekly, bi-weekly, or monthly cycles in performance
2. **Trend Changes**: Gradual improvements or degradations over time  
3. **Seasonal Effects**: End-of-sprint rushes, holiday impacts, etc.
4. **Rhythm Disruptions**: Breaks in otherwise consistent patterns

Focus on patterns that suggest:
- Team rhythm and working patterns
- External factors affecting flow
- Process changes that worked or didn't work
- Predictable performance variations

Only report patterns with clear evidence. Format as JSON:
{{
  "patterns": [
    {{
      "type": "temporal_pattern",
      "description": "What pattern you observed",
      "evidence": "Specific time periods and data points",
      "confidence": 0.7,
      "impact": "low",
      "recommendation": "How to leverage or address this pattern"
    }}
  ]
}}"""

        try:
            if dry_run:
                print("\n" + "="*80)
                print("🔍 PATTERN ANALYZER - TEMPORAL PATTERNS (DRY RUN)")
                print("="*80)
                print("PROMPT:")
                print("-" * 40)
                print(prompt)
                print("-" * 40)
                print("="*80)
                return {"patterns": []}
            
            if not self.llm:
                return {"patterns": []}
            response = self.llm.generate_insights(prompt, raw_data, dry_run)
            return self._parse_json_response(response)
        except Exception as e:
            logger.warning(f"Temporal pattern analysis failed: {e}")
            return {"patterns": []}
    
    def _analyze_cross_correlations(self, raw_data: Dict, imperative_insights: Dict, dry_run: bool) -> Dict:
        """Analyze correlations between different metrics."""
        prompt = f"""Analyze CROSS-METRIC CORRELATIONS in this flow data:

MULTIPLE METRICS DATA:
{self._format_correlation_data(raw_data)}

Look for UNEXPECTED RELATIONSHIPS between metrics:

1. **Inverse Correlations**: When one metric improves, another degrades
2. **Delayed Effects**: Changes in one metric affecting others later
3. **Threshold Effects**: Metrics that change behavior at certain levels
4. **Compound Patterns**: Multiple metrics changing together in unusual ways

Examples to investigate:
- WIP increases but cycle time stays flat (capacity constraint?)
- Throughput stable but quality metrics declining (technical debt?)
- Bottlenecks shifting between stages (process optimization effects?)

Only report correlations with clear evidence. Format as JSON:
{{
  "patterns": [
    {{
      "type": "cross_correlation",
      "description": "Relationship between metrics X and Y",
      "evidence": "Specific data showing this correlation",
      "confidence": 0.6,
      "impact": "high",
      "hypothesis": "Possible explanation for this relationship"
    }}
  ]
}}"""

        try:
            if dry_run:
                print("\n" + "="*80)
                print("🔍 PATTERN ANALYZER - CROSS-CORRELATIONS (DRY RUN)")
                print("="*80)
                print("PROMPT:")
                print("-" * 40)
                print(prompt)
                print("-" * 40)
                print("="*80)
                return {"patterns": []}
            
            if not self.llm:
                return {"patterns": []}
            response = self.llm.generate_insights(prompt, raw_data, dry_run)
            return self._parse_json_response(response)
        except Exception as e:
            logger.warning(f"Cross-correlation analysis failed: {e}")
            return {"patterns": []}
    
    def _build_basic_pattern_prompt(self, raw_data: Dict, imperative_insights: Dict) -> str:
        """Build a single comprehensive pattern detection prompt."""
        return f"""You are an expert agile coach analyzing team flow metrics. 

CURRENT ANALYSIS (from imperative rules):
{json.dumps(imperative_insights, indent=2, default=str)}

RAW DATA:
{self._format_raw_data_summary(raw_data)}

Your task: Identify SUBTLE PATTERNS that the rule-based analysis might have missed.

Look for:
1. Unusual correlations between metrics
2. Temporal patterns (weekly/monthly cycles)
3. Early warning indicators
4. Hidden constraints or bottlenecks
5. Quality-related flow impacts

Only report patterns you can clearly evidence from the data. Include confidence scores.

Format your response as structured insights with evidence."""
    
    def _format_time_series_data(self, raw_data: Dict) -> str:
        """Format time-series data for AI analysis."""
        formatted = []
        
        # Format throughput data if available
        if "throughput" in raw_data:
            throughput_data = raw_data["throughput"]
            if hasattr(throughput_data, 'to_dict'):
                formatted.append(f"THROUGHPUT: {throughput_data.to_dict()}")
        
        # Format WIP data if available  
        if "wip" in raw_data:
            wip_data = raw_data["wip"]
            if hasattr(wip_data, 'to_dict'):
                formatted.append(f"WIP: {wip_data.to_dict()}")
        
        # Format CFD data if available
        if "cfd" in raw_data:
            cfd_data = raw_data["cfd"]
            if hasattr(cfd_data, 'to_dict'):
                # Limit CFD data to avoid token overflow
                formatted.append(f"CFD (last 10 periods): {cfd_data.tail(10).to_dict()}")
        
        return "\n".join(formatted) if formatted else "No time-series data available"
    
    def _format_correlation_data(self, raw_data: Dict) -> str:
        """Format data for correlation analysis."""
        # Similar to time-series but focus on relationships
        return self._format_time_series_data(raw_data)
    
    def _format_raw_data_summary(self, raw_data: Dict) -> str:
        """Format raw data summary for basic analysis."""
        summary = []
        
        for key, data in raw_data.items():
            if hasattr(data, 'describe'):
                # Pandas DataFrame/Series
                summary.append(f"{key.upper()}: {data.describe().to_dict()}")
            elif isinstance(data, dict):
                summary.append(f"{key.upper()}: {data}")
        
        return "\n".join(summary) if summary else "No data available"
    
    def _parse_pattern_response(self, response: str, confidence_base: float = 0.7) -> Dict:
        """Parse AI response into structured pattern data."""
        try:
            # Try to parse as JSON first
            if response.strip().startswith('{'):
                parsed = json.loads(response)
                # Ensure it has the expected structure
                if "patterns" in parsed:
                    return {
                        "status": "success",
                        "patterns": parsed["patterns"],
                        "total_patterns": len(parsed["patterns"])
                    }
                else:
                    return parsed
        except json.JSONDecodeError:
            pass
        
        # Fallback: parse as text and structure it
        patterns = []
        lines = response.split('\n')
        
        current_pattern = None
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Look for pattern indicators
            if any(keyword in line.lower() for keyword in ['pattern:', 'anomaly:', 'correlation:', 'trend:']):
                if current_pattern:
                    patterns.append(current_pattern)
                
                current_pattern = {
                    "type": "ai_detected",
                    "description": line,
                    "confidence": confidence_base,
                    "impact": "medium"
                }
            elif current_pattern and line.startswith('-'):
                # Add evidence or details
                if "evidence" not in current_pattern:
                    current_pattern["evidence"] = []
                current_pattern["evidence"].append(line[1:].strip())
        
        if current_pattern:
            patterns.append(current_pattern)
        
        return {
            "status": "success",
            "patterns": patterns,
            "total_patterns": len(patterns)
        }
    
    def _parse_json_response(self, response: str) -> Dict:
        """Parse JSON response from AI."""
        try:
            # Clean up response - remove markdown code blocks if present
            cleaned = response.strip()
            if cleaned.startswith('```json'):
                cleaned = cleaned[7:]
            if cleaned.endswith('```'):
                cleaned = cleaned[:-3]
            
            return json.loads(cleaned.strip())
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON response: {e}")
            return {"patterns": []}
