"""
AI-powered insights generator for agile team coaching.
Generates daily briefings and actionable recommendations.
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional
from .providers import LLMFactory

logger = logging.getLogger(__name__)


class InsightsGenerator:
    """Generates AI-powered insights from agile metrics context."""
    
    def __init__(self, ai_config: Dict):
        self.config = ai_config
        self.llm = LLMFactory.create_provider(ai_config)
    
    def generate_daily_insights(self, context_file: str, output_file: str = 'daily-insights.md') -> str:
        """Generate daily insights from context file."""
        try:
            with open(context_file, 'r') as f:
                context = json.load(f)
            
            prompt = self._build_daily_insights_prompt(context)
            insights = self.llm.generate_insights(prompt, context)
            
            # Format and save insights
            formatted_insights = self._format_daily_insights(insights, context)
            
            with open(output_file, 'w') as f:
                f.write(formatted_insights)
            
            logger.info(f"Daily insights generated: {output_file}")
            return formatted_insights
            
        except FileNotFoundError:
            error_msg = f"Context file not found: {context_file}"
            logger.error(error_msg)
            return f"Error: {error_msg}"
        except Exception as e:
            error_msg = f"Error generating insights: {str(e)}"
            logger.error(error_msg)
            return f"Error: {error_msg}"
    
    def generate_chat_response(self, question: str, context_file: str) -> Dict:
        """Generate response to a specific question about the metrics."""
        try:
            with open(context_file, 'r') as f:
                context = json.load(f)
            
            prompt = self._build_chat_prompt(question, context)
            response = self.llm.generate_insights(prompt, context)
            
            return {
                "answer": response,
                "context_timestamp": context['metadata']['generated_at'],
                "sources": self._extract_ticket_references(response)
            }
            
        except Exception as e:
            return {
                "answer": f"Error: {str(e)}",
                "context_timestamp": None,
                "sources": []
            }
    
    def _build_daily_insights_prompt(self, context: Dict) -> str:
        """Build prompt for daily insights generation."""
        metadata = context.get('metadata', {})
        metrics = context.get('metrics_summary', {})
        issues = context.get('specific_issues', [])
        patterns = context.get('patterns_detected', [])
        
        # Calculate sprint progress
        sprint_day = self._calculate_sprint_day(metadata.get('sprint_info', {}))
        
        prompt = f"""Generate a daily team lead briefing based on the following agile metrics data:

TEAM CONTEXT:
- Team: {metadata.get('team_name', 'Unknown')}
- Sprint: {metadata.get('sprint_info', {}).get('current_sprint', 'Unknown')} (Day {sprint_day}/10)
- Analysis Period: {metadata.get('analysis_period_days', 14)} days
- Total Issues: {metadata.get('total_issues_analyzed', 0)}

CURRENT METRICS:
{self._format_metrics_for_prompt(metrics)}

SPECIFIC ISSUES REQUIRING ATTENTION:
{self._format_issues_for_prompt(issues[:10])}  # Limit to top 10

DETECTED PATTERNS:
{self._format_patterns_for_prompt(patterns)}

REQUIREMENTS:
1. Provide 3-5 prioritized, actionable recommendations
2. Focus on immediate actions for today/this week
3. Include specific ticket IDs for verification
4. Identify the top bottleneck and suggest concrete steps
5. Keep recommendations concise and practical

Format your response as a structured daily briefing suitable for a team lead."""
        
        return prompt
    
    def _build_chat_prompt(self, question: str, context: Dict) -> str:
        """Build prompt for chat-style questions."""
        return f"""Answer the following question about the team's agile metrics:

QUESTION: {question}

AVAILABLE DATA:
{json.dumps(context, indent=2, default=str)}

CONSTRAINTS:
- Only use information explicitly provided in the data above
- If the question asks about data not available, say "I don't have that information"
- Include ticket IDs when referencing specific issues
- Provide actionable insights when possible"""
    
    def _calculate_sprint_day(self, sprint_info: Dict) -> int:
        """Calculate which day of the sprint we're on."""
        try:
            start_date = sprint_info.get('sprint_start')
            if not start_date:
                return 1
            
            if isinstance(start_date, str):
                start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            else:
                start = start_date
            
            days_elapsed = (datetime.now() - start).days + 1
            return max(1, min(days_elapsed, 10))  # Assume 10-day sprints
        except:
            return 1
    
    def _format_metrics_for_prompt(self, metrics: Dict) -> str:
        """Format metrics summary for the prompt."""
        lines = []
        
        if 'cycle_time' in metrics:
            ct = metrics['cycle_time']
            if 'error' not in ct:
                lines.append(f"- Cycle Time: {ct.get('current_average', 'N/A')} days average")
        
        if 'throughput' in metrics:
            tp = metrics['throughput']
            lines.append(f"- Throughput: {tp.get('current_week', 'N/A')} items/week")
        
        if 'wip' in metrics:
            wip = metrics['wip']
            lines.append(f"- WIP: {wip.get('current_count', 'N/A')}/{wip.get('limit', 'N/A')} ({wip.get('status', 'unknown')})")
        
        if 'aging_wip' in metrics:
            aging = metrics['aging_wip']
            lines.append(f"- Aging WIP: {aging.get('items_over_10_days', 0)} items >10 days")
        
        return '\n'.join(lines) if lines else "No metrics available"
    
    def _format_issues_for_prompt(self, issues: List[Dict]) -> str:
        """Format issue list for the prompt."""
        if not issues:
            return "No specific issues identified"
        
        lines = []
        for issue in issues:
            status_info = f"Status: {issue.get('status', 'Unknown')}"
            if issue.get('days_in_current_status'):
                status_info += f" ({issue['days_in_current_status']} days)"
            
            blocked_info = " [BLOCKED]" if issue.get('blocked') else ""
            
            lines.append(f"- {issue.get('ticket_id', 'Unknown')}: {issue.get('title', 'No title')[:60]}...")
            lines.append(f"  {status_info}, Assignee: {issue.get('assignee', 'Unassigned')}{blocked_info}")
        
        return '\n'.join(lines)
    
    def _format_patterns_for_prompt(self, patterns: List[Dict]) -> str:
        """Format detected patterns for the prompt."""
        if not patterns:
            return "No significant patterns detected"
        
        lines = []
        for pattern in patterns:
            lines.append(f"- {pattern.get('description', 'Unknown pattern')} (confidence: {pattern.get('confidence', 0):.0%})")
            
            # Add supporting data if available
            supporting = pattern.get('supporting_data', {})
            if supporting:
                for key, value in supporting.items():
                    lines.append(f"  {key}: {value}")
        
        return '\n'.join(lines)
    
    def _format_daily_insights(self, insights: str, context: Dict) -> str:
        """Format the AI-generated insights into a structured daily briefing."""
        metadata = context.get('metadata', {})
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        header = f"""# Daily Agile Team Briefing
**Generated:** {timestamp}
**Team:** {metadata.get('team_name', 'Unknown')}
**Sprint:** {metadata.get('sprint_info', {}).get('current_sprint', 'Unknown')}
**Data Source:** {metadata.get('jira_query', 'Unknown query')}

---

"""
        
        footer = f"""

---

**Verification Notes:**
- All ticket IDs mentioned above can be verified in JIRA
- Metrics are based on {metadata.get('total_issues_analyzed', 0)} issues from the last {metadata.get('analysis_period_days', 14)} days
- Context generated at: {metadata.get('generated_at', 'Unknown')}

**Next Steps:**
1. Review the specific tickets mentioned above
2. Discuss top priority items in today's standup
3. Take action on the recommended interventions
"""
        
        return header + insights + footer
    
    def _extract_ticket_references(self, text: str) -> List[str]:
        """Extract ticket ID references from text for verification."""
        import re
        
        # Common JIRA ticket patterns: PROJ-123, ABC-456, etc.
        pattern = r'\b[A-Z]{2,10}-\d+\b'
        matches = re.findall(pattern, text)
        return list(set(matches))  # Remove duplicates
