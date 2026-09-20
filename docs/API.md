# CodeMemory Local API Documentation

This API serves the local CodeMemory desktop application frontend (Next.js).

## Base URL
`http://localhost:8000/api/v1`

## Endpoints

### 1. Health
- `GET /health`: Returns the overall service and storage tier health.

### 2. Dashboard
- `GET /dashboard`: Aggregated dashboard metrics, analytics, and revision queue.

### 3. Problems
- `GET /problems`: Paginated list of all problems with basic Python-side filtering (`search`, `difficulty`, `status`).
- `GET /problems/{slug}`: Get full problem details including attempts and submissions.

### 4. Submissions
- `GET /submissions`: Paginated list of flattened submissions across all problems.
- `GET /submissions/{id}`: Get a specific submission by ID.

### 5. Analytics
- `GET /analytics?granularity=day`: Detailed analytics including topics, difficulty, language, and progress over time.

### 6. Knowledge
- `GET /knowledge`: The knowledge graph nodes and edges.

### 7. Revision
- `GET /revision?topic=xyz`: Get the current revision queue based on spaced repetition scores.
- `POST /revision/{slug}/reviewed`: Mark a problem as reviewed.

### 8. LeetCode
- `GET /leetcode/status`: Check LeetCode sync status and connection state.
- `POST /leetcode/connect`: Provide username to connect to LeetCode public API.
- `POST /leetcode/sync`: Trigger a synchronous update.
- `DELETE /leetcode/connect`: Disconnect.

### 9. Settings
- `GET /settings`: Returns local application configuration and statuses (like `autosync_enabled`, `data_dir`).

## Error Handling
All errors follow the `ErrorResponse` schema:
```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable message."
  }
}
```
Standard codes: `NOT_FOUND`, `VALIDATION_ERROR`, `ERROR`, `INTERNAL_ERROR`.
