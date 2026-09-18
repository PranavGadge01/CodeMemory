"""Personal DSA memory service ('My Patterns') analyzing long-term practice history."""

from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional
from pydantic import BaseModel, Field
from codememory.domain.models import Problem, Submission


class PersonalPatternSummary(BaseModel):
    """Structured summary of a developer's personal DSA patterns."""

    strengths: List[str] = Field(description="Top mastered topics and algorithms")
    weaknesses: List[str] = Field(description="Struggle topics with high fail/TLE rates")
    frequent_approaches: List[str] = Field(description="Most frequently utilized problem-solving techniques")
    frequent_mistakes: List[str] = Field(description="Common failure modes and bug patterns")
    neglected_topics: List[str] = Field(description="Topics not practiced recently")
    revisited_problems: List[str] = Field(description="Problems attempted 3+ times")
    preferred_languages: Dict[str, float] = Field(description="Language usage percentage distribution")
    avg_attempts_to_solve: float = Field(description="Average attempts required to reach accepted solution")
    improvement_insights: List[str] = Field(description="Traceable insights on accuracy and runtime improvements")


class MyPatternsService:
    """Service for computing data-driven personal DSA practice insights."""

    def analyze_patterns(self, problems: List[Problem], submissions: List[Submission]) -> PersonalPatternSummary:
        """Analyze complete historical practice data into actionable personal patterns."""
        if not problems or not submissions:
            return PersonalPatternSummary(
                strengths=["No practice data recorded yet"],
                weaknesses=["No practice data recorded yet"],
                frequent_approaches=[],
                frequent_mistakes=[],
                neglected_topics=[],
                revisited_problems=[],
                preferred_languages={},
                avg_attempts_to_solve=0.0,
                improvement_insights=["Start solving problems to unlock personalized DSA insights."],
            )

        # 1. Topic performance metrics
        topic_total: Dict[str, int] = {}
        topic_accepted: Dict[str, int] = {}
        topic_fails: Dict[str, int] = {}
        topic_last_date: Dict[str, datetime] = {}

        # 2. Languages distribution
        lang_counts: Dict[str, int] = {}

        # 3. Mistakes & Approaches
        mistakes_counter: Dict[str, int] = {}
        approaches_counter: Dict[str, int] = {}

        # 4. Group submissions by problem
        problem_subs: Dict[str, List[Submission]] = {}
        for sub in submissions:
            problem_subs.setdefault(sub.problem_id, []).append(sub)

            lang = sub.language.lower()
            lang_counts[lang] = lang_counts.get(lang, 0) + 1

        now = datetime.now(timezone.utc)
        revisited_problems_list: List[str] = []
        total_solved_attempts = 0
        solved_count = 0

        for problem in problems:
            subs = problem_subs.get(problem.id, [])
            if len(subs) >= 3:
                revisited_problems_list.append(problem.title)

            for attempt in problem.attempts:
                for mist in attempt.mistakes:
                    mistakes_counter[mist.strip()] = mistakes_counter.get(mist.strip(), 0) + 1
                if attempt.reasoning:
                    approaches_counter[attempt.reasoning.strip()] = approaches_counter.get(attempt.reasoning.strip(), 0) + 1
                elif attempt.approach_summary:
                    approaches_counter[attempt.approach_summary.strip()] = approaches_counter.get(attempt.approach_summary.strip(), 0) + 1

            is_solved = any(s.status.value == "Accepted" for s in subs)
            if is_solved:
                solved_count += 1
                total_solved_attempts += len(subs)

            for topic in problem.topics:
                topic_total[topic] = topic_total.get(topic, 0) + len(subs)
                if is_solved:
                    topic_accepted[topic] = topic_accepted.get(topic, 0) + 1
                for s in subs:
                    if s.status.value != "Accepted":
                        topic_fails[topic] = topic_fails.get(topic, 0) + 1
                    if s.submitted_at:
                        ts = s.submitted_at if s.submitted_at.tzinfo else s.submitted_at.replace(tzinfo=timezone.utc)
                        if topic not in topic_last_date or ts > topic_last_date[topic]:
                            topic_last_date[topic] = ts

        # Compute Strengths & Weaknesses
        strengths: List[str] = []
        weaknesses: List[str] = []

        for topic, total_subs in topic_total.items():
            acc = topic_accepted.get(topic, 0)
            fails = topic_fails.get(topic, 0)

            if acc > 0 and fails == 0:
                strengths.append(f"{topic} (100% acceptance across {acc} problems)")
            elif fails > acc:
                weaknesses.append(f"{topic} ({fails} failed attempts vs {acc} solved)")

        if not strengths:
            top_topics = sorted(topic_accepted.items(), key=lambda x: x[1], reverse=True)[:3]
            strengths = [f"{t[0]} ({t[1]} solved)" for t in top_topics] if top_topics else ["General Problem Solving"]

        if not weaknesses:
            weaknesses = ["No major weak topics identified yet!"]

        # Neglected topics (> 30 days or oldest practiced)
        cutoff = now - timedelta(days=30)
        neglected: List[str] = []
        for topic, last_dt in topic_last_date.items():
            if last_dt < cutoff:
                days_ago = (now - last_dt).days
                neglected.append(f"{topic} (last practiced {days_ago} days ago)")

        if not neglected and topic_last_date:
            sorted_by_date = sorted(topic_last_date.items(), key=lambda x: x[1])
            oldest_topic, dt = sorted_by_date[0]
            days = (now - dt).days
            neglected.append(f"{oldest_topic} (longest time since practice: {days} days)")

        # Preferred languages %
        total_langs = sum(lang_counts.values()) or 1
        preferred_languages = {lang: round((count / total_langs) * 100, 1) for lang, count in lang_counts.items()}

        avg_attempts_to_solve = round(total_solved_attempts / solved_count, 2) if solved_count > 0 else 0.0

        # Improvement insights
        improvement_insights = [
            f"Average of {avg_attempts_to_solve} attempts needed to solve a problem.",
            f"Practiced in {len(lang_counts)} programming languages ({', '.join(lang_counts.keys())}).",
        ]
        if revisited_problems_list:
            improvement_insights.append(f"Revisited {len(revisited_problems_list)} complex problems multiple times to master optimal approaches.")

        top_mistakes = sorted(mistakes_counter.items(), key=lambda x: x[1], reverse=True)[:3]
        frequent_mistakes_list = [f"{m[0]} ({m[1]}x)" for m in top_mistakes] if top_mistakes else ["Boundary condition checks", "Off-by-one indices"]

        top_approaches = sorted(approaches_counter.items(), key=lambda x: x[1], reverse=True)[:3]
        frequent_approaches_list = [f"{a[0]} ({a[1]}x)" for a in top_approaches] if top_approaches else ["Hash Table Lookup", "Two Pointers Strategy"]

        return PersonalPatternSummary(
            strengths=strengths[:5],
            weaknesses=weaknesses[:5],
            frequent_approaches=frequent_approaches_list,
            frequent_mistakes=frequent_mistakes_list,
            neglected_topics=neglected[:5],
            revisited_problems=revisited_problems_list,
            preferred_languages=preferred_languages,
            avg_attempts_to_solve=avg_attempts_to_solve,
            improvement_insights=improvement_insights,
        )
