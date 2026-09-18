"""Multi-criteria search engine for CodeMemory."""

from datetime import datetime, timezone
import re
from typing import Any, Sequence

from codememory.domain.enums import DifficultyLevel, SubmissionStatus
from codememory.domain.models import Problem
from codememory.storage.composite_repository import CompositeStorage


class SearchService:
    """Search engine supporting multi-criteria filtering across problems, attempts, and submissions."""

    def __init__(self, storage: CompositeStorage):
        self.storage = storage

    def search(
        self,
        query: str | None = None,
        topics: list[str] | str | None = None,
        difficulty: str | DifficultyLevel | None = None,
        language: str | None = None,
        status: str | SubmissionStatus | None = None,
        from_date: datetime | str | None = None,
        to_date: datetime | str | None = None,
        min_attempts: int | None = None,
        max_attempts: int | None = None,
        solved: bool | None = None,
    ) -> list[Problem]:
        """Execute multi-criteria search filtering over stored problems."""
        all_problems = self.storage.list_all()
        results: list[Problem] = []

        # Parse filter targets
        target_diff = DifficultyLevel.parse(difficulty).value if difficulty else None
        target_status = SubmissionStatus.parse(status).value if status else None
        target_lang = str(language).strip().lower() if language else None

        topic_list: list[str] = []
        if isinstance(topics, str):
            topic_list = [t.strip().lower() for t in topics.split(",") if t.strip()]
        elif isinstance(topics, list):
            topic_list = [str(t).strip().lower() for t in topics if str(t).strip()]

        from_dt = self._parse_dt(from_date)
        to_dt = self._parse_dt(to_date)

        for p in all_problems:
            # 1. Solved / Unsolved filter
            is_solved = p.latest_accepted_submission is not None
            if solved is True and not is_solved:
                continue
            if solved is False and is_solved:
                continue

            # 2. Difficulty filter
            p_diff = p.difficulty.value if hasattr(p.difficulty, "value") else str(p.difficulty)
            if target_diff and target_diff != "Unknown" and p_diff != target_diff:
                continue

            # 3. Topic filter
            if topic_list:
                prob_topics_lower = [t.lower() for t in p.topics]
                if not any(any(t_kw in pt for pt in prob_topics_lower) for t_kw in topic_list):
                    continue

            # 4. Attempt count filter
            p_att_count = len(p.attempts)
            if min_attempts is not None and p_att_count < min_attempts:
                continue
            if max_attempts is not None and p_att_count > max_attempts:
                continue

            # 5. Language & Status & Date Range inspection across submissions
            all_subs = []
            for a in p.attempts:
                all_subs.extend(a.submissions)

            if target_lang:
                if not any(s.language.lower() == target_lang for s in all_subs):
                    continue

            if target_status:
                if not any((s.status.value if hasattr(s.status, "value") else str(s.status)) == target_status for s in all_subs):
                    continue

            if from_dt or to_dt:
                def _to_utc(dt: datetime | None) -> datetime | None:
                    if dt is None: return None
                    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt

                f_dt = _to_utc(from_dt)
                t_dt = _to_utc(to_dt)
                matches_date = False

                for s in all_subs:
                    s_dt = _to_utc(s.submitted_at)
                    if s_dt is not None:
                        if f_dt and s_dt < f_dt:
                            continue
                        if t_dt and s_dt > t_dt:
                            continue
                        matches_date = True
                        break
                if not matches_date and all_subs:
                    continue

            # 6. Free text query match
            if query and query.strip():
                q_lower = query.strip().lower()
                text_match = False

                # Title or slug match
                if q_lower in p.title.lower() or q_lower in p.slug.lower():
                    text_match = True
                elif p.statement and q_lower in p.statement.lower():
                    text_match = True
                else:
                    for a in p.attempts:
                        if a.reasoning and q_lower in a.reasoning.lower():
                            text_match = True
                            break
                        for s in a.submissions:
                            if q_lower in s.code.lower():
                                text_match = True
                                break
                        if text_match:
                            break

                if not text_match:
                    continue

            results.append(p)

        return results

    def search_by_query_string(self, query_string: str) -> list[Problem]:
        """Helper interpreting common natural phrases into multi-criteria searches."""
        q = query_string.strip().lower()

        # Check phrase intents
        if "tle" in q or "time limit" in q:
            return self.search(status=SubmissionStatus.TIME_LIMIT_EXCEEDED)
        if "wrong answer" in q or "wa" in q:
            return self.search(status=SubmissionStatus.WRONG_ANSWER)
        if "more than" in q and "attempt" in q:
            match = re.search(r"more than (\d+) attempt", q)
            if match:
                min_att = int(match.group(1)) + 1
                return self.search(min_attempts=min_att)
            return self.search(min_attempts=3)
        if "unsolved" in q:
            return self.search(solved=False)

        # Fallback to topic or keyword search
        return self.search(query=query_string, topics=query_string)

    def _parse_dt(self, dt: Any) -> datetime | None:
        if isinstance(dt, datetime):
            if dt.tzinfo is None:
                return dt.replace(tzinfo=timezone.utc)
            return dt
        if isinstance(dt, str) and dt.strip():
            try:
                d = datetime.fromisoformat(dt.replace("Z", "+00:00"))
                if d.tzinfo is None:
                    return d.replace(tzinfo=timezone.utc)
                return d
            except ValueError:
                pass
        return None
