"""LeetCode GraphQL client wrapper providing public API connectivity for account sync."""

import json
import logging

from typing import Any, Dict, List, Optional
import urllib.request

from codememory.connectors.leetcode.models import LeetCodeProblemRaw, LeetCodeSubmissionRaw

logger = logging.getLogger(__name__)

LEETCODE_GRAPHQL_URL = "https://leetcode.com/graphql"


class LeetCodeClient:
    """GraphQL client for communicating with official public LeetCode GraphQL endpoints."""

    def __init__(self, session_cookie: Optional[str] = None):
        self.session_cookie = session_cookie

    def _headers(self) -> Dict[str, str]:
        """Construct standard HTTP headers for LeetCode GraphQL requests."""
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://leetcode.com",
        }
        if self.session_cookie:
            headers["Cookie"] = f"LEETCODE_SESSION={self.session_cookie}"
        return headers

    def execute_query(self, query: str, variables: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Execute GraphQL POST query against official LeetCode endpoint."""
        payload = json.dumps({"query": query, "variables": variables or {}}).encode("utf-8")
        req = urllib.request.Request(LEETCODE_GRAPHQL_URL, data=payload, headers=self._headers(), method="POST")

        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode("utf-8"))
                    return data
        except Exception as e:
            logger.warning("LeetCode GraphQL request failed: %s", e)
            return None
        return None

    def fetch_user_profile(self, username: str) -> Optional[Dict[str, Any]]:
        """Fetch public profile, avatar, ranking, and solved breakdown via GraphQL."""
        query = """
        query userPublicProfile($username: String!) {
            matchedUser(username: $username) {
                username
                profile {
                    realName
                    userAvatar
                    ranking
                }
                submitStats {
                    acSubmissionNum {
                        difficulty
                        count
                    }
                }
            }
        }
        """
        result = self.execute_query(query, {"username": username})
        if not result or "data" not in result or not result["data"].get("matchedUser"):
            return None

        user_data = result["data"]["matchedUser"]
        profile = user_data.get("profile", {})
        stats = user_data.get("submitStats", {}).get("acSubmissionNum", [])

        difficulty_counts = {item.get("difficulty"): item.get("count", 0) for item in stats}

        return {
            "username": user_data.get("username", username),
            "real_name": profile.get("realName"),
            "user_avatar": profile.get("userAvatar"),
            "ranking": profile.get("ranking"),
            "solved_all": difficulty_counts.get("All", 0),
            "solved_easy": difficulty_counts.get("Easy", 0),
            "solved_medium": difficulty_counts.get("Medium", 0),
            "solved_hard": difficulty_counts.get("Hard", 0),
        }

    def fetch_user_submissions(self, username: str, limit: int = 20) -> List[LeetCodeSubmissionRaw]:
        """Fetch recent user accepted submissions via public GraphQL query."""
        query = """
        query recentAcSubmissions($username: String!, $limit: Int!) {
            recentAcSubmissionList(username: $username, limit: $limit) {
                id
                title
                titleSlug
                timestamp
                statusDisplay
                lang
            }
        }
        """
        result = self.execute_query(query, {"username": username, "limit": limit})
        if not result or "data" not in result or not result["data"].get("recentAcSubmissionList"):
            return []

        raw_submissions = []
        for item in result["data"]["recentAcSubmissionList"]:
            raw_submissions.append(
                LeetCodeSubmissionRaw(
                    id=item.get("id"),
                    submission_id=item.get("id"),
                    title=item.get("title", ""),
                    title_slug=item.get("titleSlug"),
                    language=item.get("lang", "python3"),
                    status=item.get("statusDisplay", "Accepted"),
                    timestamp=item.get("timestamp"),
                )
            )
        return raw_submissions

    def fetch_problem_details(self, problem_slug: str) -> Optional[LeetCodeProblemRaw]:
        """Fetch problem details (title, difficulty, topics, content) via GraphQL query."""
        query = """
        query questionData($titleSlug: String!) {
            question(titleSlug: $titleSlug) {
                questionId
                title
                titleSlug
                difficulty
                content
                topicTags {
                    name
                }
            }
        }
        """
        result = self.execute_query(query, {"titleSlug": problem_slug})
        if not result or "data" not in result or not result["data"].get("question"):
            return None

        q = result["data"]["question"]
        topics = [t["name"] for t in q.get("topicTags", []) if "name" in t]
        return LeetCodeProblemRaw(
            id=q.get("questionId"),
            question_id=q.get("questionId"),
            title=q.get("title", problem_slug.replace("-", " ").title()),
            title_slug=q.get("titleSlug", problem_slug),
            difficulty=q.get("difficulty"),
            topics=topics,
            url=f"https://leetcode.com/problems/{problem_slug}/",
            content=q.get("content"),
        )
