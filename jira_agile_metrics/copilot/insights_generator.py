"""
AI-powered insights generator for agile team coaching.
Generates daily briefings and actionable recommendations.
"""

import json
import logging
from datetime import datetime
from typing import Dict, List
from .providers import LLMFactory

logger = logging.getLogger(__name__)


class InsightsGenerator:
    """Generates AI-powered insights from agile metrics context."""

    def __init__(self, ai_config: Dict):
        self.config = ai_config
        self.llm = LLMFactory.create_provider(ai_config)

    def generate_daily_insights(
        self, context_file: str, output_file: str = "daily-insights.md"
    ) -> str:
        """Generate daily insights from context file."""
        try:
            with open(context_file, "r") as f:
                context = json.load(f)

            prompt = self._build_daily_insights_prompt(context)
            insights = self.llm.generate_insights(prompt, context)

            # Format and save insights
            formatted_insights = self._format_daily_insights(insights, context)

            with open(output_file, "w") as f:
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
            with open(context_file, "r") as f:
                context = json.load(f)

            prompt = self._build_chat_prompt(question, context)
            response = self.llm.generate_insights(prompt, context)

            return {
                "answer": response,
                "context_timestamp": context["metadata"]["generated_at"],
                "sources": self._extract_ticket_references(response),
            }

        except Exception as e:
            return {
                "answer": f"Error: {str(e)}",
                "context_timestamp": None,
                "sources": [],
            }

    def _build_daily_insights_prompt(self, context: Dict) -> str:
        """Build prompt for flow-focused daily insights generation."""
        metadata = context.get("metadata", {})
        flow_health = context.get("flow_health", {})
        ageing_wip = context.get("ageing_wip_analysis", {})
        throughput = context.get("throughput_trends", {})
        wip_stability = context.get("wip_stability", {})
        bottlenecks = context.get("bottleneck_detection", {})
        actionable_items = context.get("actionable_items", [])

        prompt = f"""You are an experienced agile team lead with deep expertise in flow metrics and Actionable Agile principles.
Generate a daily team briefing based on the following flow analysis:

FLOW HEALTH OVERVIEW:
{self._format_flow_health_for_prompt(flow_health)}

WORK IN PROGRESS ANALYSIS:
{self._format_wip_analysis_for_prompt(ageing_wip, wip_stability)}

THROUGHPUT & PREDICTABILITY:
{self._format_throughput_for_prompt(throughput)}

BOTTLENECK DETECTION:
{self._format_bottlenecks_for_prompt(bottlenecks)}

ITEMS REQUIRING IMMEDIATE ATTENTION:
{self._format_actionable_items_for_prompt(actionable_items)}

WORKFLOW CONFIGURATION:
- Stages: {' → '.join(metadata.get('workflow_stages', []))}
- Committed Stage: {metadata.get('committed_column', 'Unknown')}
- Done Stage: {metadata.get('done_column', 'Unknown')}

As an experienced flow metrics expert, provide:

1. **Flow Health Assessment**: Overall team flow health with specific metrics
2. **Priority Actions**: 3-4 specific, actionable recommendations with ticket IDs
3. **Bottleneck Analysis**: Primary constraint and concrete steps to address it
4. **Predictability Insights**: Team's delivery predictability and improvement areas
5. **Leading Indicators**: Early warning signs to watch for

Focus on:
- Actionable insights that improve flow efficiency
- Specific ticket IDs for verification
- Evidence-based recommendations using provided metrics
- Practical steps the team can take today/this week

Format as a professional team lead briefing."""

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
            start_date = sprint_info.get("sprint_start")
            if not start_date:
                return 1

            if isinstance(start_date, str):
                start = datetime.fromisoformat(
                    start_date.replace("Z", "+00:00")
                )
            else:
                start = start_date

            days_elapsed = (datetime.now() - start).days + 1
            return max(1, min(days_elapsed, 10))  # Assume 10-day sprints
        except Exception:
            return 1

    def _format_metrics_for_prompt(self, metrics: Dict) -> str:
        """Format metrics summary for the prompt."""
        lines = []

        if "cycle_time" in metrics:
            ct = metrics["cycle_time"]
            if "error" not in ct:
                lines.append(
                    f"- Cycle Time: {ct.get('current_average', 'N/A')} days average"
                )

        if "throughput" in metrics:
            tp = metrics["throughput"]
            lines.append(
                f"- Throughput: {tp.get('current_week', 'N/A')} items/week"
            )

        if "wip" in metrics:
            wip = metrics["wip"]
            lines.append(
                f"- WIP: {wip.get('current_count', 'N/A')}/{wip.get('limit', 'N/A')} ({wip.get('status', 'unknown')})"
            )

        if "aging_wip" in metrics:
            aging = metrics["aging_wip"]
            lines.append(
                f"- Aging WIP: {aging.get('items_over_10_days', 0)} items >10 days"
            )

        return "\n".join(lines) if lines else "No metrics available"

    def _format_issues_for_prompt(self, issues: List[Dict]) -> str:
        """Format issue list for the prompt."""
        if not issues:
            return "No specific issues identified"

        lines = []
        for issue in issues:
            status_info = f"Status: {issue.get('status', 'Unknown')}"
            if issue.get("days_in_current_status"):
                status_info += f" ({issue['days_in_current_status']} days)"

            blocked_info = " [BLOCKED]" if issue.get("blocked") else ""

            lines.append(
                f"- {issue.get('ticket_id', 'Unknown')}: {issue.get('title', 'No title')[:60]}..."
            )
            lines.append(
                f"  {status_info}, Assignee: {issue.get('assignee', 'Unassigned')}{blocked_info}"
            )

        return "\n".join(lines)

    def _format_patterns_for_prompt(self, patterns: List[Dict]) -> str:
        """Format detected patterns for the prompt."""
        if not patterns:
            return "No significant patterns detected"

        lines = []
        for pattern in patterns:
            lines.append(
                f"- {pattern.get('description', 'Unknown pattern')} (confidence: {pattern.get('confidence', 0):.0%})"
            )

            # Add supporting data if available
            supporting = pattern.get("supporting_data", {})
            if supporting:
                for key, value in supporting.items():
                    lines.append(f"  {key}: {value}")

        return "\n".join(lines)

    def _format_daily_insights(self, insights: str, context: Dict) -> str:
        """Format the AI-generated insights into a structured daily briefing."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        metadata = context.get("metadata", {})

        # Extract key metrics for header
        flow_health = context.get("flow_health", {})
        wip_count = context.get("ageing_wip_analysis", {}).get(
            "total_wip_items", 0
        )
        throughput_trend = context.get("throughput_trends", {}).get(
            "trend_direction", "unknown"
        )

        formatted = f"""# Daily Flow Metrics Briefing - {timestamp}

## Flow Overview
- **Workflow**: {' → '.join(metadata.get('workflow_stages', ['Unknown']))}
- **Current WIP**: {wip_count} items
- **Avg Cycle Time**: {flow_health.get('avg_cycle_time', 0):.1f} days
- **Throughput Trend**: {throughput_trend.title()}
- **Predictability**: {flow_health.get('predictability_ratio', 0):.1f}x median

## Expert Analysis

{insights}

---
*Generated by AI Flow Metrics Copilot | Based on Actionable Agile principles*
"""

        return formatted

    def _extract_ticket_references(self, text: str) -> List[str]:
        """Extract ticket ID references from text for verification."""
        import re

        # Common JIRA ticket patterns: PROJ-123, ABC-456, etc.
        pattern = r"\b[A-Z]{2,10}-\d+\b"
        matches = re.findall(pattern, text)
        return list(set(matches))  # Remove duplicates

    def _format_flow_health_for_prompt(self, flow_health: Dict) -> str:
        """Format flow health metrics for prompt."""
        if flow_health.get("status") == "no_completed_items":
            return "⚠️  No completed items found - unable to assess flow health"

        if flow_health.get("status") == "error":
            return f"❌ Error analyzing flow health: {flow_health.get('message', 'Unknown error')}"

        predictability = flow_health.get("predictability_ratio", 0)
        predictability_status = (
            "🟢 Excellent"
            if predictability < 2
            else "🟡 Moderate" if predictability < 3 else "🔴 Poor"
        )

        return f"""- Completed Items: {flow_health.get('total_completed_items', 0)}
- Average Cycle Time: {flow_health.get('avg_cycle_time', 0):.1f} days
- Median Cycle Time: {flow_health.get('median_cycle_time', 0):.1f} days
- 85th Percentile: {flow_health.get('percentile_85', 0):.1f} days
- Predictability Ratio: {predictability:.1f} {predictability_status}
- Cycle Time Std Dev: {flow_health.get('cycle_time_std', 0):.1f} days"""

    def _format_wip_analysis_for_prompt(
        self, ageing_wip: Dict, wip_stability: Dict
    ) -> str:
        """Format WIP analysis for prompt."""
        wip_section = []

        # Ageing WIP Analysis
        if ageing_wip.get("status") == "no_wip_items":
            wip_section.append("✅ No work in progress items")
        elif ageing_wip.get("status") == "error":
            wip_section.append(
                f"❌ WIP Analysis Error: {ageing_wip.get('message')}"
            )
        else:
            stuck_count = ageing_wip.get("stuck_items_count", 0)
            stuck_status = (
                "🔴" if stuck_count > 3 else "🟡" if stuck_count > 1 else "🟢"
            )

            wip_section.append(
                f"""Current WIP: {ageing_wip.get('total_wip_items', 0)} items
Average Age: {ageing_wip.get('avg_age_days', 0):.1f} days
Oldest Item: {ageing_wip.get('oldest_item_age', 0):.0f} days
Stuck Items: {stuck_count} {stuck_status}"""
            )

            # Add stuck items details
            stuck_items = ageing_wip.get("stuck_items", [])
            if stuck_items:
                wip_section.append("\nStuck Items:")
                for item in stuck_items[:5]:  # Top 5
                    wip_section.append(
                        f"  - {item['key']} ({item['age_days']}d): {item['summary']}"
                    )

        # WIP Stability
        if wip_stability.get("status") != "error":
            trend_emoji = (
                "📈"
                if wip_stability.get("wip_trend") == "increasing"
                else (
                    "📉"
                    if wip_stability.get("wip_trend") == "decreasing"
                    else "➡️"
                )
            )
            wip_section.append(
                f"\nWIP Trend: {wip_stability.get('wip_trend', 'unknown')} {trend_emoji}"
            )
            wip_section.append(
                f"Current WIP: {wip_stability.get('current_wip', 0):.0f}"
            )
            wip_section.append(
                f"Average WIP: {wip_stability.get('avg_wip', 0):.1f}"
            )

            if "net_flow_trend" in wip_stability:
                flow_emoji = (
                    "⚠️"
                    if wip_stability.get("net_flow_trend") == "growing"
                    else (
                        "✅"
                        if wip_stability.get("net_flow_trend") == "shrinking"
                        else "🔄"
                    )
                )
                wip_section.append(
                    f"Net Flow: {wip_stability.get('net_flow_trend', 'unknown')} {flow_emoji}"
                )

        return "\n".join(wip_section)

    def _format_throughput_for_prompt(self, throughput: Dict) -> str:
        """Format throughput analysis for prompt."""
        if throughput.get("status") == "no_throughput_data":
            return "⚠️  No throughput data available"

        if throughput.get("status") == "error":
            return f"❌ Throughput Analysis Error: {throughput.get('message')}"

        trend = throughput.get("trend_direction", "unknown")
        trend_emoji = (
            "📈"
            if trend == "improving"
            else "📉" if trend == "declining" else "➡️"
        )

        volatility = throughput.get("throughput_volatility", 0)
        volatility_status = (
            "🟢 Stable"
            if volatility < 2
            else "🟡 Moderate" if volatility < 4 else "🔴 Volatile"
        )

        return f"""Recent Avg Throughput: {throughput.get('recent_avg_throughput', 0):.1f} items/period
Historical Avg: {throughput.get('historical_avg_throughput', 0):.1f} items/period
Trend: {trend} {trend_emoji} (Δ{throughput.get('trend_magnitude', 0):.1f})
Volatility: {volatility:.1f} {volatility_status}
Range: {throughput.get('min_throughput', 0):.0f} - {throughput.get('max_throughput', 0):.0f} items"""

    def _format_bottlenecks_for_prompt(self, bottlenecks: Dict) -> str:
        """Format bottleneck analysis for prompt."""
        if bottlenecks.get("status") == "no_cfd_data":
            return "⚠️  No CFD data available for bottleneck analysis"

        if bottlenecks.get("status") == "error":
            return (
                f"❌ Bottleneck Analysis Error: {bottlenecks.get('message')}"
            )

        bottleneck_list = bottlenecks.get("potential_bottlenecks", [])

        if not bottleneck_list:
            return "✅ No significant bottlenecks detected"

        result = [
            f"🚨 {len(bottleneck_list)} potential bottleneck(s) detected:"
        ]

        for bottleneck in bottleneck_list:
            result.append(
                f"  - {bottleneck['stage']}: +{bottleneck['growth_rate']:.1f} items/week ({bottleneck['current_count']:.0f} current)"
            )

        return "\n".join(result)

    def _format_actionable_items_for_prompt(
        self, actionable_items: List[Dict]
    ) -> str:
        """Format actionable items for prompt."""
        if not actionable_items:
            return "✅ No items requiring immediate attention"

        result = [f"🎯 {len(actionable_items)} item(s) need attention:"]

        for item in actionable_items:
            priority_emoji = "🔴" if item.get("priority") == "high" else "🟡"
            result.append(
                f"  {priority_emoji} {item['key']} ({item['age_days']}d): {item['summary']}"
            )
            result.append(
                f"     Reason: {item.get('reason', 'unknown')} (threshold: {item.get('threshold_exceeded', 0):.1f}d)"
            )

        return "\n".join(result)
