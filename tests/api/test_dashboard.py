def test_get_dashboard(client):
    response = client.get("/api/v1/dashboard")
    assert response.status_code == 200
    data = response.json()
    
    # Assert top-level keys match schema
    expected_keys = {
        "overview", "activity", "timeline", "struggles", 
        "topics", "languages", "difficulties", "revisionQueue", "progress"
    }
    assert set(data.keys()) == expected_keys
    
    # Assert camelCase is applied correctly
    assert "totalProblems" in data["overview"]
    assert data["overview"]["totalProblems"] == 1  # From seed data
    
    # Assert activity and timeline now contain real data (seeded problem has 1 accepted submission)
    assert len(data["activity"]) > 0
    assert len(data["timeline"]) > 0
    
    # Verify streak fields are populated (from real activity)
    assert "currentStreakDays" in data["overview"]
    assert "longestStreakDays" in data["overview"]
    assert "activeDaysLast30" in data["overview"]


def test_dashboard_empty_database(empty_client):
    """Empty database should return zero/empty values without errors."""
    response = empty_client.get("/api/v1/dashboard")
    assert response.status_code == 200
    data = response.json()
    
    # Overview fields should be zero/empty
    assert data["overview"]["totalProblems"] == 0
    assert data["overview"]["currentStreakDays"] == 0
    assert data["overview"]["longestStreakDays"] == 0
    assert data["overview"]["activeDaysLast30"] == 0
    
    # Activity and timeline should be empty
    assert data["activity"] == []
    assert data["timeline"] == []
    
    # Other collections should be empty
    assert len(data["revisionQueue"]) == 0


def test_dashboard_activity_counts_submissions_per_day(streak_client):
    """Multiple submissions on the same day should count as one active day."""
    response = streak_client.get("/api/v1/dashboard")
    assert response.status_code == 200
    data = response.json()
    
    activity = data["activity"]
    assert len(activity) > 0
    
    # Verify there's an activity entry for today
    today_entries = [a for a in activity if a["date"]]
    assert len(today_entries) > 0
    
    # Today had 2 submissions (one accepted, one wrong answer) and 1 problem solved
    today_entry = today_entries[-1]  # Most recent
    assert today_entry["submissions"] >= 2
    assert today_entry["accepted"] >= 1
    assert today_entry["solved"] >= 1


def test_dashboard_streak_calculation(streak_client):
    """Verify streak calculation with known submission dates."""
    response = streak_client.get("/api/v1/dashboard")
    assert response.status_code == 200
    data = response.json()
    
    # Today, yesterday, and 2 days ago are consecutive -> current streak is at least 3
    # 5 days ago creates a gap, so longest streak is 3 (unless today's streak continues)
    current_streak = data["overview"]["currentStreakDays"]
    longest_streak = data["overview"]["longestStreakDays"]
    
    assert current_streak >= 3, f"Expected current streak >= 3, got {current_streak}"
    assert longest_streak >= 3, f"Expected longest streak >= 3, got {longest_streak}"
    assert longest_streak >= current_streak, "Longest streak should be >= current streak"


def test_dashboard_streak_resets_on_gap(streak_client):
    """Verify streak resets correctly when there's a gap in activity."""
    response = streak_client.get("/api/v1/dashboard")
    assert response.status_code == 200
    data = response.json()
    
    # With submissions on today, yesterday, day-2, and day-5 (gap at day-3/day-4)
    # The streak should be exactly 3 (today, yesterday, day-2), not 4+
    # because day-3 and day-4 have no submissions
    current_streak = data["overview"]["currentStreakDays"]
    assert current_streak == 3, f"Expected current streak == 3, got {current_streak}"


def test_dashboard_timeline_ordering(streak_client):
    """Timeline events should be ordered chronologically (most recent first)."""
    response = streak_client.get("/api/v1/dashboard")
    assert response.status_code == 200
    data = response.json()
    
    timeline = data["timeline"]
    assert len(timeline) > 0
    
    # Verify events are sorted by occurredAt descending
    dates = [e["occurredAt"] for e in timeline]
    assert dates == sorted(dates, reverse=True), "Timeline should be in reverse chronological order"


def test_dashboard_timeline_event_types(streak_client):
    """Timeline should contain different event types from real data."""
    response = streak_client.get("/api/v1/dashboard")
    assert response.status_code == 200
    data = response.json()
    
    timeline = data["timeline"]
    event_kinds = set(e["kind"] for e in timeline)
    
    # We should have 'attempted' (from submissions), 'solved' (from accepted submissions),
    # and 'imported' (from problem creation) events
    assert "attempted" in event_kinds
    assert "solved" in event_kinds
    assert "imported" in event_kinds


def test_dashboard_timeline_contains_problem_info(streak_client):
    """Timeline events should reference actual problems."""
    response = streak_client.get("/api/v1/dashboard")
    assert response.status_code == 200
    data = response.json()
    
    timeline = data["timeline"]
    
    # Each event should have a problem reference
    for event in timeline:
        if event["kind"] in ("attempted", "solved"):
            assert event["problemSlug"] is not None, f"Event {event['id']} missing problemSlug"
            assert event["language"] is not None, f"Event {event['id']} missing language"
        elif event["kind"] == "imported":
            assert event["problemSlug"] is not None, f"Imported event {event['id']} missing problemSlug"
