"""LeetCode integration capability declaration."""

LEETCODE_CAPABILITIES = {
    "profile_sync": True,
    "progress_sync": True,
    "recent_submissions": True,
    "private_code_scraping": False,
}

LEETCODE_CAPABILITY_EXPLANATIONS = {
    "profile_sync": "Synchronize public profile info, real name, ranking, and avatar.",
    "progress_sync": "Synchronize total solved problem counts by difficulty (Easy, Medium, Hard).",
    "recent_submissions": "Synchronize recent public submission titles, languages, timestamps, and status.",
    "private_code_scraping": "Unauthorized code scraping/cookie stealing is disabled to comply with LeetCode Terms.",
}
