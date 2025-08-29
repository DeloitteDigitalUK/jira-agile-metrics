"""
Context file generator that creates structured data for AI consumption.
Focused on flow analysis rather than sprint-based metrics.
"""

import json
import logging
import pandas as pd

from datetime import datetime
from typing import Dict, List
from ..calculator import Calculator

logger = logging.getLogger(__name__)


class AIContextGenerator(Calculator):
    """Generates structured context files for AI flow analysis."""
    
    def __init__(self, query_manager, settings, results):
        super().__init__(query_manager, settings, results)
        self.context_data = {}
    
    def run(self):
        """Generate AI context from existing calculator results focused on flow analysis."""
        logger.info("Generating AI context data for flow analysis...")
        
        # Get cycle time data as foundation
        from ..calculators.cycletime import CycleTimeCalculator
        
        cycle_data = self._results.get(CycleTimeCalculator)
        if cycle_data is None:
            logger.error("No cycle time data available for AI context generation")
            return {}
        
        self.context_data = {
            "metadata": self._generate_metadata(),
            "flow_health": self._analyze_flow_health(cycle_data),
            "ageing_wip_analysis": self._analyze_ageing_wip(),
            "throughput_trends": self._analyze_throughput_trends(),
            "wip_stability": self._analyze_wip_stability(),
            "bottleneck_detection": self._detect_bottlenecks(),
            "cycle_time_patterns": self._analyze_cycle_time_patterns(cycle_data),
            "actionable_items": self._identify_actionable_items(cycle_data)
        }
        
        # Write context file
        output_file = self.settings.get('ai_context_file', 'ai-context.json')
        with open(output_file, 'w') as f:
            json.dump(self.context_data, f, indent=2, default=str)
        
        logger.info(f"AI context written to {output_file}")
        return self.context_data
    
    def _generate_metadata(self) -> Dict:
        """Generate metadata about the analysis period and configuration."""
        return {
            "analysis_date": datetime.now().isoformat(),
            "workflow_stages": [s["name"] for s in self.settings["cycle"]],
            "committed_column": self.settings["committed_column"],
            "done_column": self.settings["done_column"],
            "backlog_column": self.settings["backlog_column"]
        }
    
    def _analyze_flow_health(self, cycle_data) -> Dict:
        """Analyze overall flow health metrics."""
        import pandas as pd
        
        done_column = self.settings["done_column"]
        
        # Get completed items
        completed_items = cycle_data[pd.notna(cycle_data[done_column])].copy()
        
        if len(completed_items) == 0:
            return {"status": "no_completed_items", "message": "No completed items found"}
        
        # Calculate key metrics
        cycle_times = completed_items['cycle_time'].dropna()
        
        return {
            "total_completed_items": len(completed_items),
            "avg_cycle_time": float(cycle_times.mean()) if len(cycle_times) > 0 else 0,
            "median_cycle_time": float(cycle_times.median()) if len(cycle_times) > 0 else 0,
            "cycle_time_std": float(cycle_times.std()) if len(cycle_times) > 0 else 0,
            "percentile_85": float(cycle_times.quantile(0.85)) if len(cycle_times) > 0 else 0,
            "predictability_ratio": float(cycle_times.quantile(0.85) / cycle_times.median()) if len(cycle_times) > 0 and cycle_times.median() > 0 else 0
        }
    
    def _analyze_ageing_wip(self) -> Dict:
        """Analyze work in progress for ageing and stuck items."""
        from ..calculators.ageingwip import AgeingWIPChartCalculator
        
        try:
            ageing_calc = AgeingWIPChartCalculator(self.query_manager, self.settings, self._results)
            ageing_data = ageing_calc.run()
            
            if ageing_data is None or len(ageing_data) == 0:
                return {"status": "no_wip_items", "message": "No work in progress items found"}
            
            # Analyze ageing patterns
            ages = ageing_data['age']
            avg_age = float(ages.mean())
            
            # Identify stuck items (age > 2x average)
            stuck_threshold = avg_age * 2 if avg_age > 0 else 14  # fallback to 2 weeks
            stuck_items = ageing_data[ageing_data['age'] > stuck_threshold]
            
            return {
                "total_wip_items": len(ageing_data),
                "avg_age_days": avg_age,
                "oldest_item_age": float(ages.max()),
                "stuck_items_count": len(stuck_items),
                "stuck_items": [
                    {
                        "key": row['key'],
                        "summary": row['summary'][:100] if pd.notna(row.get('summary')) else "No summary",
                        "status": row['status'],
                        "age_days": int(row['age'])
                    }
                    for _, row in stuck_items.head(10).iterrows()  # limit to top 10
                ],
                "status_distribution": ageing_data['status'].value_counts().to_dict()
            }
        except Exception as e:
            logger.warning(f"Error analyzing ageing WIP: {e}")
            return {"status": "error", "message": str(e)}
    
    def _analyze_throughput_trends(self) -> Dict:
        """Analyze throughput trends and patterns."""
        from ..calculators.throughput import ThroughputCalculator
        
        try:
            throughput_calc = ThroughputCalculator(self.query_manager, self.settings, self._results)
            throughput_data = throughput_calc.run()
            
            if throughput_data is None or len(throughput_data) == 0:
                return {"status": "no_throughput_data", "message": "No throughput data available"}
            
            # Calculate trend metrics
            recent_period = throughput_data.tail(4)  # last 4 periods
            older_period = throughput_data.head(len(throughput_data) - 4) if len(throughput_data) > 4 else throughput_data
            
            recent_avg = recent_period['count'].mean() if len(recent_period) > 0 else 0
            historical_avg = older_period['count'].mean() if len(older_period) > 0 else recent_avg
            
            trend_direction = "improving" if recent_avg > historical_avg else "declining" if recent_avg < historical_avg else "stable"
            
            return {
                "total_periods": len(throughput_data),
                "recent_avg_throughput": float(recent_avg),
                "historical_avg_throughput": float(historical_avg),
                "trend_direction": trend_direction,
                "trend_magnitude": float(abs(recent_avg - historical_avg)),
                "max_throughput": float(throughput_data['count'].max()),
                "min_throughput": float(throughput_data['count'].min()),
                "throughput_volatility": float(throughput_data['count'].std())
            }
        except Exception as e:
            logger.warning(f"Error analyzing throughput trends: {e}")
            return {"status": "error", "message": str(e)}
    
    def _analyze_wip_stability(self) -> Dict:
        """Analyze WIP stability and net flow patterns."""
        from ..calculators.wip import WIPChartCalculator
        from ..calculators.netflow import NetFlowChartCalculator
        
        try:
            wip_calc = WIPChartCalculator(self.query_manager, self.settings, self._results)
            wip_data = wip_calc.run()
            
            if wip_data is None or len(wip_data) == 0:
                return {"status": "no_wip_data", "message": "No WIP data available"}
            
            wip_values = wip_data['wip']
            current_wip = float(wip_values.iloc[-1]) if len(wip_values) > 0 else 0
            avg_wip = float(wip_values.mean())
            wip_trend = "increasing" if current_wip > avg_wip * 1.1 else "decreasing" if current_wip < avg_wip * 0.9 else "stable"
            
            result = {
                "current_wip": current_wip,
                "avg_wip": avg_wip,
                "max_wip": float(wip_values.max()),
                "wip_volatility": float(wip_values.std()),
                "wip_trend": wip_trend
            }
            
            # Add net flow analysis if available
            try:
                netflow_calc = NetFlowChartCalculator(self.query_manager, self.settings, self._results)
                netflow_data = netflow_calc.run()
                
                if netflow_data is not None and len(netflow_data) > 0:
                    recent_netflow = netflow_data['net_flow'].tail(4).mean()
                    result.update({
                        "recent_net_flow": float(recent_netflow),
                        "net_flow_trend": "growing" if recent_netflow > 0.5 else "shrinking" if recent_netflow < -0.5 else "balanced"
                    })
            except Exception:
                pass  # Net flow analysis is optional
            
            return result
        except Exception as e:
            logger.warning(f"Error analyzing WIP stability: {e}")
            return {"status": "error", "message": str(e)}
    
    def _detect_bottlenecks(self) -> Dict:
        """Detect bottlenecks using CFD analysis."""
        from ..calculators.cfd import CFDCalculator
        
        try:
            cfd_calc = CFDCalculator(self.query_manager, self.settings, self._results)
            cfd_data = cfd_calc.run()
            
            if cfd_data is None or len(cfd_data) == 0:
                return {"status": "no_cfd_data", "message": "No CFD data available"}
            
            # Analyze stage growth rates to detect bottlenecks
            stage_analysis = {}
            workflow_stages = [s["name"] for s in self.settings["cycle"]]
            
            for stage in workflow_stages:
                if stage in cfd_data.columns:
                    stage_data = cfd_data[stage].diff().tail(7)  # last week's changes
                    avg_growth = stage_data.mean()
                    stage_analysis[stage] = {
                        "avg_weekly_growth": float(avg_growth),
                        "current_count": float(cfd_data[stage].iloc[-1]) if len(cfd_data) > 0 else 0
                    }
            
            # Identify potential bottlenecks (stages with high growth)
            bottlenecks = []
            for stage, metrics in stage_analysis.items():
                if metrics["avg_weekly_growth"] > 2:  # growing by more than 2 items per week
                    bottlenecks.append({
                        "stage": stage,
                        "growth_rate": metrics["avg_weekly_growth"],
                        "current_count": metrics["current_count"]
                    })
            
            return {
                "stage_analysis": stage_analysis,
                "potential_bottlenecks": bottlenecks,
                "bottleneck_count": len(bottlenecks)
            }
        except Exception as e:
            logger.warning(f"Error detecting bottlenecks: {e}")
            return {"status": "error", "message": str(e)}
    
    def _analyze_cycle_time_patterns(self, cycle_data) -> Dict:
        """Analyze cycle time patterns and trends."""
        import pandas as pd
        
        try:
            done_column = self.settings["done_column"]
            completed_items = cycle_data[pd.notna(cycle_data[done_column])].copy()
            
            if len(completed_items) == 0:
                return {"status": "no_completed_items", "message": "No completed items for pattern analysis"}
            
            # Analyze by issue type if available
            patterns = {}
            if 'issue_type' in completed_items.columns:
                type_analysis = completed_items.groupby('issue_type')['cycle_time'].agg([
                    'count', 'mean', 'median', 'std'
                ]).round(2)
                patterns['by_issue_type'] = type_analysis.to_dict('index')
            
            # Analyze recent vs historical performance
            if len(completed_items) > 10:
                recent_items = completed_items.tail(10)
                historical_items = completed_items.head(len(completed_items) - 10)
                
                recent_avg = recent_items['cycle_time'].mean()
                historical_avg = historical_items['cycle_time'].mean()
                
                patterns['performance_trend'] = {
                    "recent_avg_cycle_time": float(recent_avg),
                    "historical_avg_cycle_time": float(historical_avg),
                    "trend": "improving" if recent_avg < historical_avg else "declining" if recent_avg > historical_avg else "stable"
                }
            
            return patterns
        except Exception as e:
            logger.warning(f"Error analyzing cycle time patterns: {e}")
            return {"status": "error", "message": str(e)}
    
    def _identify_actionable_items(self, cycle_data) -> List[Dict]:
        """Identify specific items requiring attention."""
        import pandas as pd
        
        actionable_items = []
        
        try:
            done_column = self.settings["done_column"]
            committed_column = self.settings["committed_column"]
            
            # Get WIP items
            wip_items = cycle_data[pd.isnull(cycle_data[done_column])].copy()
            
            if len(wip_items) == 0:
                return actionable_items
            
            # Calculate ages for WIP items
            today = pd.Timestamp.now().date()
            
            def calculate_age(row):
                if pd.isnull(row[committed_column]):
                    return None
                return (today - row[committed_column].date()).days
            
            wip_items['age'] = wip_items.apply(calculate_age, axis=1)
            wip_items = wip_items.dropna(subset=['age'])
            
            if len(wip_items) == 0:
                return actionable_items
            
            # Identify outliers (age > 85th percentile of completed cycle times)
            completed_items = cycle_data[pd.notna(cycle_data[done_column])]
            if len(completed_items) > 0:
                cycle_times = completed_items['cycle_time'].dropna()
                if len(cycle_times) > 0:
                    outlier_threshold = cycle_times.quantile(0.85)
                    outliers = wip_items[wip_items['age'] > outlier_threshold]
                    
                    for _, item in outliers.head(5).iterrows():  # top 5 outliers
                        actionable_items.append({
                            "key": item['key'],
                            "summary": item['summary'][:100] if pd.notna(item.get('summary')) else "No summary",
                            "age_days": int(item['age']),
                            "reason": "ageing_outlier",
                            "threshold_exceeded": float(outlier_threshold),
                            "priority": "high" if item['age'] > outlier_threshold * 1.5 else "medium"
                        })
            
            return actionable_items
        except Exception as e:
            logger.warning(f"Error identifying actionable items: {e}")
            return actionable_items
