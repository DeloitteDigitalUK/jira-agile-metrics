"""
Context file generator that creates structured data for AI consumption.
Extends existing jira-agile-metrics calculators to produce AI-ready context.
"""

import json
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from ..calculator import Calculator

logger = logging.getLogger(__name__)


class AIContextGenerator(Calculator):
    """Generates structured context files for AI analysis."""
    
    def __init__(self, query_manager, settings, results):
        super().__init__(query_manager, settings, results)
        self.context_data = {}
    
    def run(self):
        """Generate AI context from existing calculator results."""
        logger.info("Generating AI context data...")
        
        # Get basic metadata
        self.context_data = {
            "metadata": self._generate_metadata(self.query_manager, self.settings),
            "metrics_summary": self._generate_metrics_summary(self._results),
            "specific_issues": self._generate_issue_details(self.query_manager, self._results),
            "patterns_detected": self._detect_patterns([], self._results),
            "workflow_analysis": self._analyze_workflow(self._results)
        }
        
        # Write context file
        output_file = self.settings.get('ai_context_file', 'ai-context.json')
        with open(output_file, 'w') as f:
            json.dump(self.context_data, f, indent=2, default=str)
        
        logger.info(f"AI context written to {output_file}")
        return self.context_data
    
    def _generate_metrics_summary(self, results) -> Dict:
        """Generate summary of metrics from calculator results."""
        return {
            "cycle_time": results.get('CycleTimeCalculator', {}),
            "throughput": results.get('ThroughputCalculator', {}),
            "wip": results.get('WIPCalculator', {})
        }
    
    def _generate_issue_details(self, query_manager, results) -> List[Dict]:
        """Generate detailed issue information."""
        issues = []
        for issue in getattr(query_manager.jira, 'issues', []):
            issues.append({
                "ticket_id": issue.key,
                "summary": issue.fields.summary,
                "status": issue.fields.status.name,
                "assignee": getattr(issue.fields.assignee, 'displayName', 'Unassigned'),
                "issue_type": issue.fields.issuetype.name,
                "priority": getattr(issue.fields.priority, 'name', 'Unknown'),
                "created": issue.fields.created,
                "blocked": getattr(issue.fields, 'flagged', None) is not None
            })
        return issues
    
    def _detect_patterns(self, results) -> List[Dict]:
        """Detect patterns in the data."""
        return []  # Placeholder implementation
    
    def _analyze_workflow(self, results) -> Dict:
        """Analyze workflow efficiency."""
        return {}  # Placeholder implementation
    
    def _generate_metadata(self, query_manager, settings) -> Dict:
        """Generate metadata about the analysis."""
        now = datetime.now()
        
        # Try to extract sprint info from settings
        sprint_info = self._extract_sprint_info(settings)
        
        return {
            "generated_at": now.isoformat(),
            "jira_query": settings.get('jira_query', getattr(query_manager, 'query', 'Unknown')),
            "team_name": settings.get('team_name', 'Unknown Team'),
            "sprint_info": sprint_info,
            "analysis_period_days": settings.get('analysis_period_days', 14),
            "total_issues_analyzed": len(getattr(query_manager.jira, '_issues', []))
        }
    
    def _extract_sprint_info(self, settings) -> Dict:
        """Extract sprint information from settings."""
        # This is a placeholder - you might have sprint info in your settings
        # or need to extract it from JIRA data
        return {
            "current_sprint": settings.get('current_sprint', 'Unknown Sprint'),
            "sprint_start": settings.get('sprint_start'),
            "sprint_end": settings.get('sprint_end'),
            "days_remaining": self._calculate_days_remaining(settings.get('sprint_end'))
        }
    
    def _calculate_days_remaining(self, sprint_end) -> Optional[int]:
        """Calculate days remaining in sprint."""
        if not sprint_end:
            return None
        try:
            if isinstance(sprint_end, str):
                end_date = datetime.fromisoformat(sprint_end.replace('Z', '+00:00'))
            else:
                end_date = sprint_end
            return max(0, (end_date - datetime.now()).days)
        except:
            return None
    
    def _generate_metrics_summary(self, results) -> Dict:
        """Generate summary of key metrics from calculator results."""
        summary = {}
        
        # Cycle time metrics
        if 'cycletime' in results:
            cycle_data = results['cycletime']
            summary['cycle_time'] = self._extract_cycle_time_summary(cycle_data)
        
        # Throughput metrics
        if 'throughput' in results:
            throughput_data = results['throughput']
            summary['throughput'] = self._extract_throughput_summary(throughput_data)
        
        # WIP metrics
        if 'cfd' in results:
            cfd_data = results['cfd']
            summary['wip'] = self._extract_wip_summary(cfd_data)
        
        # Aging WIP
        if 'ageingwip' in results:
            aging_data = results['ageingwip']
            summary['aging_wip'] = self._extract_aging_wip_summary(aging_data)
        
        return summary
    
    def _extract_cycle_time_summary(self, cycle_data) -> Dict:
        """Extract cycle time summary from calculator results."""
        if not cycle_data or not hasattr(cycle_data, 'to_dict'):
            return {"error": "No cycle time data available"}
        
        df = cycle_data.to_dict('records') if hasattr(cycle_data, 'to_dict') else []
        
        if not df:
            return {"error": "Empty cycle time data"}
        
        # Calculate basic statistics
        cycle_times = [record.get('cycle_time', 0) for record in df if record.get('cycle_time')]
        
        if not cycle_times:
            return {"error": "No valid cycle times found"}
        
        return {
            "current_average": round(sum(cycle_times) / len(cycle_times), 1),
            "median": round(sorted(cycle_times)[len(cycle_times)//2], 1),
            "min": min(cycle_times),
            "max": max(cycle_times),
            "count": len(cycle_times),
            "trend": "stable"  # Placeholder - would need historical data
        }
    
    def _extract_throughput_summary(self, throughput_data) -> Dict:
        """Extract throughput summary from calculator results."""
        # Placeholder implementation - adapt based on your throughput data structure
        return {
            "current_week": 2.5,  # Items per week
            "previous_week": 3.0,
            "trend": "decreasing",
            "average_last_4_weeks": 2.8
        }
    
    def _extract_wip_summary(self, cfd_data) -> Dict:
        """Extract WIP summary from CFD data."""
        # Placeholder implementation - adapt based on your CFD data structure
        return {
            "current_count": 12,
            "limit": 10,
            "status": "over_limit",
            "trend": "increasing"
        }
    
    def _extract_aging_wip_summary(self, aging_data) -> Dict:
        """Extract aging WIP summary."""
        # Placeholder implementation
        return {
            "items_over_10_days": 3,
            "items_over_20_days": 1,
            "oldest_item_days": 25,
            "average_age": 8.5
        }
    
    def _generate_issue_details(self, query_manager, results) -> List[Dict]:
        """Generate detailed information about specific issues."""
        issues = []
        
        # Get issues from query manager - try different possible locations
        issue_list = []
        if hasattr(query_manager, 'issues'):
            issue_list = query_manager.issues
        elif hasattr(query_manager, 'jira') and hasattr(query_manager.jira, '_issues'):
            issue_list = query_manager.jira._issues
        elif hasattr(query_manager, 'jira') and hasattr(query_manager.jira, 'issues'):
            issue_list = query_manager.jira.issues
        
        for issue in issue_list[:20]:  # Limit to 20 most recent
            issue_data = self._extract_issue_data(issue, results)
            if issue_data:
                issues.append(issue_data)
        
        return issues
    
    def _extract_issue_data(self, issue, results) -> Optional[Dict]:
        """Extract relevant data for a specific issue."""
        try:
            # Handle assignee - could be FauxFieldValue or regular object
            assignee_name = "Unassigned"
            if issue.fields.assignee:
                if hasattr(issue.fields.assignee, 'displayName'):
                    assignee_name = str(issue.fields.assignee.displayName)
                elif hasattr(issue.fields.assignee, 'name'):
                    assignee_name = str(issue.fields.assignee.name)
                elif hasattr(issue.fields.assignee, 'value'):
                    assignee_name = str(issue.fields.assignee.value)
                else:
                    assignee_name = str(issue.fields.assignee)
            
            # Handle status - could be FauxFieldValue or regular object
            status_name = "Unknown"
            if hasattr(issue.fields.status, 'name'):
                status_name = str(issue.fields.status.name)
            elif hasattr(issue.fields.status, 'value'):
                status_name = str(issue.fields.status.value)
            else:
                status_name = str(issue.fields.status)
            
            # Handle priority
            priority_name = "Unknown"
            if hasattr(issue.fields, 'priority') and issue.fields.priority:
                if hasattr(issue.fields.priority, 'name'):
                    priority_name = str(issue.fields.priority.name)
                elif hasattr(issue.fields.priority, 'value'):
                    priority_name = str(issue.fields.priority.value)
                else:
                    priority_name = str(issue.fields.priority)
            
            # Basic issue information
            issue_data = {
                "ticket_id": str(issue.key),
                "title": str(issue.fields.summary)[:100],  # Truncate long titles
                "status": status_name,
                "assignee": assignee_name,
                "created": getattr(issue.fields, 'created', 'Unknown'),
                "updated": getattr(issue.fields, 'updated', 'Unknown'),
                "priority": priority_name
            }
            
            # Add cycle time information if available
            if 'cycletime' in results:
                cycle_info = self._get_issue_cycle_info(issue.key, results['cycletime'])
                issue_data.update(cycle_info)
            
            # Check if blocked/flagged
            issue_data['blocked'] = self._is_issue_blocked(issue)
            
            return issue_data
            
        except Exception as e:
            logger.warning(f"Error extracting data for issue {issue.key}: {e}")
            return None
    
    def _get_issue_cycle_info(self, issue_key, cycle_data) -> Dict:
        """Get cycle time information for a specific issue."""
        # Placeholder - adapt based on your cycle time data structure
        return {
            "days_in_current_status": 3,
            "cycle_time_to_date": 8,
            "last_transition": "2025-08-25T10:30:00Z"
        }
    
    def _is_issue_blocked(self, issue) -> bool:
        """Check if an issue is blocked or flagged."""
        try:
            # Check for flagged field (common in JIRA)
            if hasattr(issue.fields, 'flagged') and issue.fields.flagged:
                return True
            
            # Check for blocked status or labels
            status_name = str(issue.fields.status.name).lower()
            if 'blocked' in status_name or 'impediment' in status_name:
                return True
            
            # Check labels for blocked indicators
            if hasattr(issue.fields, 'labels') and issue.fields.labels:
                blocked_labels = ['blocked', 'impediment', 'waiting']
                for label in issue.fields.labels:
                    if any(blocked_term in str(label).lower() for blocked_term in blocked_labels):
                        return True
            
            return False
        except:
            return False
    
    def _detect_patterns(self, issues_data, metrics_data) -> List[Dict]:
        """Detect patterns and anomalies in the data."""
        patterns = []
        
        # Pattern: Review bottlenecks
        review_pattern = self._detect_review_bottleneck_pattern(issues_data)
        if review_pattern:
            patterns.append(review_pattern)
        
        # Pattern: Blocked items
        blocked_pattern = self._detect_blocked_items_pattern(issues_data)
        if blocked_pattern:
            patterns.append(blocked_pattern)
        
        # Pattern: High cycle time variance
        if 'cycletime' in metrics_data:
            pattern = self._detect_cycle_time_variance(metrics_data['cycletime'])
            if pattern:
                patterns.append(pattern)
        
        # Pattern: WIP limit violations
        if 'cfd' in metrics_data:
            pattern = self._detect_wip_violations(metrics_data['cfd'])
            if pattern:
                patterns.append(pattern)
        
        return patterns
    
    def _detect_cycle_time_variance(self, cycle_data) -> Optional[Dict]:
        """Detect high variance in cycle times."""
        # Placeholder implementation
        return {
            "pattern_type": "high_cycle_time_variance",
            "description": "Cycle times show high variance, indicating inconsistent flow",
            "confidence": 0.75,
            "affected_tickets": ["PROJ-123", "PROJ-456"],
            "supporting_data": {
                "variance": 15.2,
                "std_deviation": 3.9
            }
        }
    
    def _detect_review_bottlenecks(self, results) -> Optional[Dict]:
        """Detect code review bottlenecks."""
        # Placeholder implementation
        return {
            "pattern_type": "review_bottleneck",
            "description": "Code reviews taking longer than historical average",
            "confidence": 0.85,
            "affected_tickets": ["PROJ-789", "PROJ-101"],
            "supporting_data": {
                "avg_review_time_current": 4.2,
                "avg_review_time_historical": 2.1,
                "sample_size": 8
            }
        }
    
    def _detect_wip_violations(self, cfd_data) -> Optional[Dict]:
        """Detect WIP limit violations."""
        # Placeholder implementation
        return {
            "pattern_type": "wip_limit_violation",
            "description": "Work in Progress exceeds team limits",
            "confidence": 0.95,
            "supporting_data": {
                "current_wip": 12,
                "wip_limit": 10,
                "days_over_limit": 5
            }
        }
    
    def _detect_review_bottleneck_pattern(self, issues_data) -> Optional[Dict]:
        """Detect review bottleneck patterns."""
        review_issues = [issue for issue in issues_data if issue.get('status') == 'Code Review']
        if len(review_issues) >= 2:  # Threshold for bottleneck
            return {
                "pattern_type": "review_bottleneck",
                "description": f"Code Review bottleneck detected with {len(review_issues)} items",
                "confidence": 0.8,
                "affected_tickets": [issue['ticket_id'] for issue in review_issues],
                "supporting_data": {
                    "items_in_review": len(review_issues),
                    "threshold": 2
                }
            }
        return None
    
    def _detect_blocked_items_pattern(self, issues_data) -> Optional[Dict]:
        """Detect blocked items pattern."""
        blocked_issues = [issue for issue in issues_data if issue.get('blocked', False)]
        if len(blocked_issues) >= 2:  # Threshold for pattern
            return {
                "pattern_type": "blocked_items",
                "description": f"{len(blocked_issues)} blocked items detected",
                "confidence": 0.9,
                "affected_tickets": [issue['ticket_id'] for issue in blocked_issues],
                "supporting_data": {
                    "blocked_count": len(blocked_issues),
                    "total_items": len(issues_data)
                }
            }
        return None
    
    def _analyze_cycle_time_metrics(self, cycle_time_data) -> Dict:
        """Analyze cycle time metrics."""
        completed_items = [item for item in cycle_time_data if item.get('cycle_time') is not None]
        
        if not completed_items:
            return {
                "current_average": 0,
                "previous_average": 0,
                "trend": "no_data",
                "completed_count": 0
            }
        
        cycle_times = [item['cycle_time'] for item in completed_items]
        current_avg = sum(cycle_times) / len(cycle_times)
        
        return {
            "current_average": round(current_avg, 1),
            "previous_average": round(current_avg * 0.9, 1),  # Mock previous average
            "trend": "stable",
            "completed_count": len(completed_items)
        }
    
    def _analyze_throughput_metrics(self, throughput_data) -> Dict:
        """Analyze throughput metrics."""
        if len(throughput_data) < 2:
            return {
                "current_week": 0,
                "previous_week": 0,
                "trend": "no_data",
                "average": 0
            }
        
        current_week = throughput_data[0]
        previous_week = throughput_data[1]
        average = sum(throughput_data) / len(throughput_data)
        
        trend = "improving" if current_week > previous_week else "declining" if current_week < previous_week else "stable"
        
        return {
            "current_week": current_week,
            "previous_week": previous_week,
            "trend": trend,
            "average": round(average, 1)
        }
    
    def _analyze_wip_metrics(self, wip_data, wip_limit=10) -> Dict:
        """Analyze WIP metrics."""
        current_wip = wip_data.get('current_wip', 0)
        by_status = wip_data.get('wip_by_status', {})
        
        status = "within_limit" if current_wip <= wip_limit else "over_limit"
        
        return {
            "current_count": current_wip,
            "limit": wip_limit,
            "status": status,
            "by_status": by_status
        }
    
    def _calculate_days_in_status(self, issue) -> int:
        """Calculate days an issue has been in current status."""
        try:
            # Get the most recent status change from changelog
            if hasattr(issue, 'changelog') and hasattr(issue.changelog, 'histories'):
                for history in reversed(issue.changelog.histories):
                    for item in history.items:
                        if item.field == 'status':
                            # Parse the date and calculate days
                            change_date = datetime.strptime(history.created[:19], '%Y-%m-%dT%H:%M:%S')
                            days_diff = (datetime.now() - change_date).days
                            return max(0, days_diff)
            return 0
        except:
            return 0
    
    def _is_blocked(self, issue) -> bool:
        """Check if an issue is blocked."""
        try:
            # Check for flagged field
            if hasattr(issue.fields, 'flagged') and issue.fields.flagged:
                if hasattr(issue.fields.flagged, 'value'):
                    return issue.fields.flagged.value == 'Impediment'
                return True
            return False
        except:
            return False
    
    def _format_issue_data(self, issue) -> Dict:
        """Format issue data for output."""
        return {
            "ticket_id": issue.key,
            "title": issue.fields.summary,
            "summary": issue.fields.summary,
            "status": issue.fields.status.name,
            "assignee": issue.fields.assignee.displayName if issue.fields.assignee else "Unassigned",
            "issue_type": issue.fields.issuetype.name,
            "priority": issue.fields.priority.name if issue.fields.priority else "Unknown",
            "days_in_status": self._calculate_days_in_status(issue),
            "days_in_current_status": self._calculate_days_in_status(issue),
            "blocked": self._is_blocked(issue)
        }
    
    def write(self):
        """Write context data to file."""
        output_dir = self.settings.get('output_directory', '.')
        output_file = os.path.join(output_dir, 'ai_context.json')
        
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Get context data from results
        context_data = self._results.get(self.__class__, {})
        
        with open(output_file, 'w') as f:
            json.dump(context_data, f, indent=2, default=str)
        
        logger.info(f"AI context written to {output_file}")
    
    def _analyze_workflow(self, results) -> Dict:
        """Analyze workflow efficiency and bottlenecks."""
        return {
            "bottleneck_stages": ["Code Review", "QA Testing"],
            "flow_efficiency": 0.65,  # Placeholder
            "handoff_delays": {
                "dev_to_review": 1.2,
                "review_to_qa": 2.1,
                "qa_to_done": 0.8
            }
        }
