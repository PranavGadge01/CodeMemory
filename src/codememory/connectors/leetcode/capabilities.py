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
    "recent_submissions": (
        "Synchronize recent public accepted submission titles, languages, and timestamps. "
        "The public sync covers only the server-bounded recent accepted-submission window — "
        "it is not a complete history, and it carries no source code, runtime, or memory. "
        "Use manual import for full exports with code and metrics."
    ),
    "private_code_scraping": "Unauthorized code scraping/cookie stealing is disabled to comply with LeetCode Terms.",
}
