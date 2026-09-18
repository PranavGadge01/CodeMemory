# Analytics, Search & Revision Engine

CodeMemory includes analytical metrics, multi-criteria search capabilities, personal pattern detection, and a deterministic revision engine.

---

## 1. Analytics Service (`AnalyticsService`)

Calculates 14 key metrics using DuckDB and Polars:

1. **Total Problems**: Unique problem entities tracked.
2. **Total Attempts**: Cumulative problem-solving sessions.
3. **Accepted Problems**: Problems with at least one accepted submission.
4. **Overall Acceptance Rate**: `(Accepted Submissions / Total Submissions) * 100`.
5. **Avg Attempts per Solved Problem**: `Total Attempts on Solved Problems / Solved Problems`.
6. **Difficulty Breakdown**: Easy, Medium, Hard problem distribution.
7. **Topic Statistics**: Success rate and acceptance rate by DSA topic.
8. **Language Statistics**: Submissions and acceptance rate by programming language.
9. **Progress Over Time**: Daily, weekly, or monthly solved problems trend.
10. **Average Solving Time**: Duration (in minutes) from first submission to first accepted submission.
11. **Struggle Problems**: Ranked list of problems with highest failed attempts/submissions.
12. **Multiple-Approach Solved Count**: Solved problems requiring > 1 approach.
13. **First-Attempt Acceptance Rate**: Percentage of solved problems accepted on attempt #1.
14. **Repeated-Problem Rate**: Percentage of problems attempted or submitted multiple times.

---

## 2. Multi-Criteria Search (`SearchService`)

Provides keyword and structured multi-attribute filtering:

```python
# Structured search
results = service.search(
    query="binary tree",
    topics=["Tree", "BFS"],
    difficulty="Medium",
    language="python",
    status="Accepted",
    solved=True
)

# Phrase intent search
results = service.search_service.search_by_query_string("problems where I got TLE")
```

---

## 3. Pattern Recognition (`PatternAnalyzer`)

Automatically detects learning trends and practice gaps:

- **Weak Topics**: Topics with < 50% success rate.
- **High Failure Topics**: Topics with < 40% submission acceptance rate.
- **Repeated TLE / WA**: Problems incurring multiple TLE or WA results.
- **Brute-Force to Optimized**: Solved problems where initial failed/slow attempt preceded optimal solution.
- **Unpracticed Topics**: Topics with zero activity in > 14 days.

---

## 4. Deterministic Revision Engine (`RevisionService`)

Assigns a revision priority score to every problem:

$$Priority = W_{diff} \cdot S_{diff} + W_{fail} \cdot S_{fail} + W_{recency} \cdot S_{recency} + W_{weakness} \cdot S_{weakness} - W_{recent\_solved} \cdot S_{recent\_solved}$$

### Default Weights (`RevisionWeights`)

- $W_{diff} = 2.0$: Hard (3.0), Medium (2.0), Easy (1.0).
- $W_{fail} = 3.0$: Up to 5.0 points for failed attempts.
- $W_{recency} = 2.5$: Scaled by days since last attempt/review (`days / 7.0`, max 10.0).
- $W_{weakness} = 2.0$: Bonus +2.0 points if problem belongs to a weak topic (<50% success rate).
- $W_{recent\_solved} = 1.5$: Penalty for problems solved within the last 3 days.

### Usage Example

```python
# Fetch top 10 prioritized problems to revise
queue = service.get_revision_queue(limit=10)

# Fetch due problems (> 7 days inactive)
due = service.get_due_problems(threshold_days=7)

# Mark a problem as reviewed
service.mark_reviewed("lru-cache", notes="Reviewed LRU doubly-linked list nodes")
```

---

## 5. Personal Insights Generator (`InsightsGenerator`)

Produces human-readable, deterministic learning statements:

- *"You struggle most with Dynamic Programming (33% success rate)."*
- *"You have solved 24 Array problems."*
- *"Your first-attempt acceptance rate across all problems is 50%."*
- *"You have not practiced Binary Search in 18 days."*
- *"Your primary programming language is Python (85% of submissions)."*
