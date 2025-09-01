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
                return {"recommendations": []}
                
            if not self.llm:
                return {"recommendations": []}
            response = self.llm.generate_insights(prompt, raw_data, dry_run)
            result = self._parse_json_response(response)
            # Convert recommendations to patterns format for compatibility
            if "recommendations" in result:
                patterns = []
                for rec in result["recommendations"]:
                    patterns.append({
                        "type": "basic_recommendation",
                        "description": rec.get("issue", ""),
                        "action": rec.get("action", ""),
                        "owner": rec.get("owner", ""),
                        "timeline": rec.get("timeline", ""),
                        "success_metric": rec.get("success_metric", ""),
                        "evidence": rec.get("evidence", ""),
                        "priority": rec.get("priority", "medium"),
                        "effort": rec.get("effort", "medium"),
                        "category": rec.get("category", "strategic"),
                        "confidence": 0.7,  # Basic analysis confidence
                        "impact": rec.get("priority", "medium")
                    })
                return {"patterns": patterns}
            return result
            
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
        """Detect flow anomalies and provide actionable recommendations."""
        prompt = f"""You are an experienced agile coach analyzing team flow metrics. Identify issues and provide SPECIFIC, ACTIONABLE recommendations.

CURRENT SITUATION:
{json.dumps(imperative_insights, indent=2, default=str)}

RAW METRICS DATA:
{self._format_time_series_data(raw_data)}

For each issue you identify, provide:

1. **ISSUE**: What specific problem do you see?
2. **ACTION**: What exact steps should the team take?
3. **OWNER**: Who should be responsible (role/person)?
4. **TIMELINE**: How long to implement and see results?
5. **SUCCESS METRIC**: How will they measure improvement?

Focus on these areas:
- Flow bottlenecks and constraints
- WIP management issues
- Cycle time variability
- Throughput inconsistencies
- Quality indicators

CRITICAL: Only recommend actions you can justify with specific data evidence.

Format as JSON:
{{
  "recommendations": [
    {{
      "issue": "Brief description of the problem",
      "action": "Specific step-by-step action to take",
      "owner": "Role or person responsible",
      "timeline": "Implementation time + expected results timeframe",
      "success_metric": "How to measure success",
      "evidence": "Specific data points supporting this recommendation",
      "priority": "high|medium|low",
      "effort": "low|medium|high"
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
                return {"recommendations": []}
            
            if not self.llm:
                return {"recommendations": []}
            response = self.llm.generate_insights(prompt, raw_data, dry_run)
            result = self._parse_json_response(response)
            # Convert recommendations to patterns format for compatibility
            if "recommendations" in result:
                patterns = []
                for rec in result["recommendations"]:
                    patterns.append({
                        "type": "actionable_recommendation",
                        "description": rec.get("issue", ""),
                        "action": rec.get("action", ""),
                        "owner": rec.get("owner", ""),
                        "timeline": rec.get("timeline", ""),
                        "success_metric": rec.get("success_metric", ""),
                        "evidence": rec.get("evidence", ""),
                        "priority": rec.get("priority", "medium"),
                        "effort": rec.get("effort", "medium"),
                        "confidence": 0.8,  # Default confidence for actionable recommendations
                        "impact": rec.get("priority", "medium")
                    })
                return {"patterns": patterns}
            return result
        except Exception as e:
            logger.warning(f"Flow anomaly analysis failed: {e}")
            return {"patterns": []}
    
    def _analyze_temporal_patterns(self, raw_data: Dict, imperative_insights: Dict, dry_run: bool) -> Dict:
        """Analyze temporal patterns and trends."""
        prompt = f"""You are an agile coach analyzing temporal patterns in team performance. Provide ACTIONABLE recommendations based on time-based trends.

TIME-SERIES DATA:
{self._format_time_series_data(raw_data)}

Analyze for temporal patterns and provide specific actions:

1. **Cyclical Patterns**: Weekly, sprint, or monthly performance cycles
2. **Trend Analysis**: Improving or degrading performance over time
3. **Seasonal Effects**: End-of-sprint rushes, holiday impacts, etc.
4. **Rhythm Issues**: Inconsistent team working patterns

For each pattern, provide:
- **ISSUE**: What temporal problem affects flow?
- **ACTION**: Specific steps to optimize timing/rhythm
- **OWNER**: Who should lead this change?
- **TIMELINE**: When to implement and measure results
- **SUCCESS METRIC**: How to track improvement

Format as JSON:
{{
  "recommendations": [
    {{
      "issue": "Specific temporal pattern affecting flow",
      "action": "Concrete steps to address timing issues",
      "owner": "Role responsible for implementation",
      "timeline": "Implementation and measurement timeframe",
      "success_metric": "How to measure timing improvements",
      "evidence": "Specific time periods and data supporting this",
      "priority": "high|medium|low",
      "effort": "low|medium|high"
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
                return {"recommendations": []}
            
            if not self.llm:
                return {"recommendations": []}
            response = self.llm.generate_insights(prompt, raw_data, dry_run)
            result = self._parse_json_response(response)
            # Convert recommendations to patterns format for compatibility
            if "recommendations" in result:
                patterns = []
                for rec in result["recommendations"]:
                    patterns.append({
                        "type": "temporal_recommendation",
                        "description": rec.get("issue", ""),
                        "action": rec.get("action", ""),
                        "owner": rec.get("owner", ""),
                        "timeline": rec.get("timeline", ""),
                        "success_metric": rec.get("success_metric", ""),
                        "evidence": rec.get("evidence", ""),
                        "priority": rec.get("priority", "medium"),
                        "effort": rec.get("effort", "medium"),
                        "confidence": 0.8,
                        "impact": rec.get("priority", "medium")
                    })
                return {"patterns": patterns}
            return result
        except Exception as e:
            logger.warning(f"Temporal pattern analysis failed: {e}")
            return {"patterns": []}
    
    def _analyze_cross_correlations(self, raw_data: Dict, imperative_insights: Dict, dry_run: bool) -> Dict:
        """Analyze cross-metric correlations and provide actionable recommendations."""
        prompt = f"""You are an agile coach analyzing cross-metric relationships in team flow data. Provide ACTIONABLE recommendations based on metric correlations.

CURRENT SITUATION:
{json.dumps(imperative_insights, indent=2, default=str)}

MULTIPLE METRICS DATA:
{self._format_correlation_data(raw_data)}

Analyze for cross-metric patterns and provide specific actions:

1. **Inverse Correlations**: When one metric improves but another degrades
2. **Delayed Effects**: Changes in one metric affecting others later
3. **Threshold Effects**: Metrics that change behavior at certain levels
4. **Compound Issues**: Multiple metrics indicating systemic problems

For each correlation pattern, provide:
- **ISSUE**: What cross-metric problem affects flow?
- **ACTION**: Specific steps to address the correlation
- **OWNER**: Who should lead this change?
- **TIMELINE**: When to implement and measure results
- **SUCCESS METRIC**: How to track correlation improvements
- **CATEGORY**: quick_wins, strategic, or foundational

Examples to investigate:
- WIP increases but cycle time stays flat (capacity constraint?)
- Throughput stable but quality declining (technical debt?)
- Bottlenecks shifting between stages (process changes?)

Format as JSON:
{{
  "recommendations": [
    {{
      "issue": "Cross-metric correlation affecting flow",
      "action": "Concrete steps to address metric relationships",
      "owner": "Role responsible for implementation",
      "timeline": "Implementation and measurement timeframe",
      "success_metric": "How to measure correlation improvements",
      "evidence": "Specific data showing this correlation",
      "priority": "high|medium|low",
      "effort": "low|medium|high",
      "category": "quick_wins|strategic|foundational"
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
                return {"recommendations": []}
            
            if not self.llm:
                return {"recommendations": []}
            response = self.llm.generate_insights(prompt, raw_data, dry_run)
            result = self._parse_json_response(response)
            # Convert recommendations to patterns format for compatibility
            if "recommendations" in result:
                patterns = []
                for rec in result["recommendations"]:
                    patterns.append({
                        "type": "correlation_recommendation",
                        "description": rec.get("issue", ""),
                        "action": rec.get("action", ""),
                        "owner": rec.get("owner", ""),
                        "timeline": rec.get("timeline", ""),
                        "success_metric": rec.get("success_metric", ""),
                        "evidence": rec.get("evidence", ""),
                        "priority": rec.get("priority", "medium"),
                        "effort": rec.get("effort", "medium"),
                        "category": rec.get("category", "strategic"),
                        "confidence": 0.7,
                        "impact": rec.get("priority", "medium")
                    })
                return {"patterns": patterns}
            return result
        except Exception as e:
            logger.warning(f"Cross-correlation analysis failed: {e}")
            return {"patterns": []}
    
    def _build_basic_pattern_prompt(self, raw_data: Dict, imperative_insights: Dict) -> str:
        """Build actionable recommendations prompt for basic analysis."""
        return f"""You are an experienced agile coach analyzing team flow metrics. Provide ACTIONABLE recommendations based on the data.

CURRENT SITUATION:
{json.dumps(imperative_insights, indent=2, default=str)}

RAW METRICS DATA:
{self._format_raw_data_summary(raw_data)}

For each issue you identify, provide:

1. **ISSUE**: What specific problem do you see?
2. **ACTION**: What exact steps should the team take?
3. **OWNER**: Who should be responsible (role/person)?
4. **TIMELINE**: How long to implement and see results?
5. **SUCCESS METRIC**: How will they measure improvement?
6. **CATEGORY**: quick_wins, strategic, or foundational

Focus on the most impactful improvements the team can make. Prioritize actions that:
- Address flow bottlenecks and constraints
- Improve predictability and cycle time
- Reduce WIP and age of work
- Enhance throughput consistency

CRITICAL: Only recommend actions you can justify with specific data evidence.

Format as JSON:
{{
  "recommendations": [
    {{
      "issue": "Brief description of the problem",
      "action": "Specific step-by-step action to take",
      "owner": "Role or person responsible",
      "timeline": "Implementation time + expected results timeframe",
      "success_metric": "How to measure success",
      "evidence": "Specific data points supporting this recommendation",
      "priority": "high|medium|low",
      "effort": "low|medium|high",
      "category": "quick_wins|strategic|foundational"
    }}
  ]
}}"""
    
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
