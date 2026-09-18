"""Deterministic Personal Insights Generator for CodeMemory."""

from typing import Sequence

from codememory.analytics.analytics_service import AnalyticsService
from codememory.analytics.pattern_analyzer import PatternAnalyzer


class InsightsGenerator:
    """Generates natural language human insights based on pattern analyzer and analytics metrics."""

    def __init__(self, analytics_service: AnalyticsService, pattern_analyzer: PatternAnalyzer | None = None):
        self.analytics = analytics_service
        self.pattern_analyzer = pattern_analyzer or PatternAnalyzer(analytics_service=analytics_service)

    def generate_insights(self) -> list[str]:
        """Generate list of actionable, deterministic natural language insights."""
        insights: list[str] = []

        overview = self.analytics.get_overview()
        if overview.total_problems == 0:
            return ["No coding problems recorded yet. Import submissions or run `codememory seed` to get started!"]

        # 1. Topic weakness insight
        topic_stats = self.analytics.get_topic_statistics()
        if topic_stats:
            weakest_topic = min(topic_stats, key=lambda t: t.success_rate_pct)
            if weakest_topic.total_problems >= 1:
                insights.append(f"You struggle most with {weakest_topic.topic} ({weakest_topic.success_rate_pct:.0f}% success rate).")

        # 2. Topic volume insight
        if topic_stats:
            most_solved_topic = max(topic_stats, key=lambda t: t.solved_problems)
            if most_solved_topic.solved_problems > 0:
                insights.append(f"You have solved {most_solved_topic.solved_problems} {most_solved_topic.topic} problems.")

        # 3. First attempt acceptance insight
        if overview.accepted_problems > 0:
            insights.append(f"Your first-attempt acceptance rate across all problems is {overview.first_attempt_acceptance_rate_pct:.0f}%.")

        # 4. Unpracticed topics insight
        patterns = self.pattern_analyzer.analyze(unpracticed_days_threshold=7)
        if patterns.unpracticed_topics:
            top_unpracticed = patterns.unpracticed_topics[0]
            insights.append(f"You have not practiced {top_unpracticed['topic']} in {top_unpracticed['days_unpracticed']} days.")

        # 5. Language usage insight
        lang_stats = self.analytics.get_language_statistics()
        if lang_stats:
            top_lang = lang_stats[0]
            insights.append(f"Your primary programming language is {top_lang.language.title()} ({top_lang.usage_share_pct:.0f}% of submissions).")

        # 6. Performance progression insight
        att_stats = self.analytics.get_attempt_statistics()
        if att_stats.brute_force_to_optimized_count > 0:
            insights.append(f"You successfully optimized brute force solutions into accepted solutions for {att_stats.brute_force_to_optimized_count} problems.")

        return insights
