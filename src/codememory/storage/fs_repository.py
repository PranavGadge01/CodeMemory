"""Filesystem and Markdown storage implementation for CodeMemory knowledge base."""

import json
from pathlib import Path
from typing import Sequence

from codememory.domain.enums import DifficultyLevel, NoteType, Platform, SubmissionStatus
from codememory.domain.models import Attempt, Problem, ProblemNote, SolutionAnalysis, Submission, generate_slug
from codememory.storage.base import AttemptRepository, ProblemRepository, SubmissionRepository

LANGUAGE_EXTENSIONS = {
    "python": ".py",
    "py": ".py",
    "python3": ".py",
    "cpp": ".cpp",
    "c++": ".cpp",
    "c": ".c",
    "java": ".java",
    "javascript": ".js",
    "js": ".js",
    "typescript": ".ts",
    "ts": ".ts",
    "rust": ".rs",
    "rs": ".rs",
    "go": ".go",
    "golang": ".go",
    "kotlin": ".kt",
    "swift": ".swift",
    "sql": ".sql",
}


def get_extension_for_language(lang: str) -> str:
    """Get standard file extension for a programming language."""
    clean_lang = str(lang or "").strip().lower()
    return LANGUAGE_EXTENSIONS.get(clean_lang, ".txt")


class FilesystemStorage(ProblemRepository, SubmissionRepository, AttemptRepository):
    """Filesystem repository producing Git-friendly Markdown and code files."""

    def __init__(self, root_dir: str | Path = "knowledge"):
        self.root_dir = Path(root_dir)
        self.root_dir.mkdir(parents=True, exist_ok=True)

    def _get_problem_dir(self, slug: str) -> Path:
        p_dir = self.root_dir / slug
        p_dir.mkdir(parents=True, exist_ok=True)
        return p_dir

    def save(self, problem: Problem) -> Problem:
        """Export problem, attempts, notes, and code files to filesystem."""
        if not problem.slug:
            problem.slug = generate_slug(problem.title)

        p_dir = self._get_problem_dir(problem.slug)

        # 1. Write problem.md
        prob_md_path = p_dir / "problem.md"
        topics_str = ", ".join(f"`{t}`" for t in problem.topics) if problem.topics else "None"
        url_str = f"[{problem.url}]({problem.url})" if problem.url else "N/A"
        stmt = problem.statement or "No problem description provided."

        prob_md_content = f"""# {problem.title}

- **Difficulty**: `{problem.difficulty.value}`
- **Platform**: `{problem.platform.value if hasattr(problem.platform, 'value') else problem.platform}`
- **Topics**: {topics_str}
- **URL**: {url_str}
- **Created**: `{problem.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}`

---

## Problem Statement

{stmt}
"""
        prob_md_path.write_text(prob_md_content, encoding="utf-8")

        # 2. Write attempts.md
        attempts_md_path = p_dir / "attempts.md"
        attempts_content = [f"# Attempts History: {problem.title}\n"]

        if not problem.attempts:
            attempts_content.append("*No attempts recorded yet.*\n")
        else:
            sorted_attempts = sorted(problem.attempts, key=lambda a: a.attempt_number)
            for attempt in sorted_attempts:
                status_badge = f"`{attempt.status.value}`"
                attempts_content.append(f"## Attempt {attempt.attempt_number}: {attempt.approach_summary}")
                attempts_content.append(f"- **Status**: {status_badge}")
                attempts_content.append(f"- **Date**: `{attempt.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}`")

                if attempt.reasoning:
                    attempts_content.append(f"- **Reasoning**: {attempt.reasoning}")

                if attempt.analysis:
                    analysis = attempt.analysis
                    attempts_content.append(f"- **Time Complexity**: `{analysis.time_complexity}`")
                    attempts_content.append(f"- **Space Complexity**: `{analysis.space_complexity}`")
                    if analysis.key_insights:
                        insights = ", ".join(analysis.key_insights)
                        attempts_content.append(f"- **Key Insights**: {insights}")

                if attempt.mistakes:
                    mistakes_str = "; ".join(attempt.mistakes)
                    attempts_content.append(f"- **Mistakes / Lessons**: {mistakes_str}")

                attempts_content.append("\n### Submissions")

                if not attempt.submissions:
                    attempts_content.append("*No code submission recorded for this attempt.*\n")
                else:
                    sorted_subs = sorted(attempt.submissions, key=lambda s: s.submitted_at)
                    for idx, sub in enumerate(sorted_subs, 1):
                        rt = f"{sub.runtime_ms:.1f} ms" if sub.runtime_ms is not None else "N/A"
                        mem = f"{sub.memory_mb:.1f} MB" if sub.memory_mb is not None else "N/A"
                        attempts_content.append(f"#### Submission {idx} ({sub.language})")
                        attempts_content.append(f"- **Result**: `{sub.status.value}` | **Runtime**: `{rt}` | **Memory**: `{mem}`")
                        attempts_content.append(f"- **Timestamp**: `{sub.submitted_at.strftime('%Y-%m-%d %H:%M:%S UTC')}`")
                        if sub.error_message:
                            attempts_content.append(f"- **Error Message**: `{sub.error_message}`")
                        ext = get_extension_for_language(sub.language).lstrip(".")
                        attempts_content.append(f"\n```{ext}\n{sub.code}\n```\n")

        attempts_md_path.write_text("\n".join(attempts_content), encoding="utf-8")

        # 3. Write solution.<ext> (Latest accepted submission code if available, else latest submission)
        target_sub = problem.latest_accepted_submission or problem.latest_submission
        if target_sub:
            ext = get_extension_for_language(target_sub.language)
            sol_path = p_dir / f"solution{ext}"
            header = f"# Solution for {problem.title}\n# Status: {target_sub.status.value}\n# Language: {target_sub.language}\n\n"
            sol_path.write_text(header + target_sub.code, encoding="utf-8")

        # 4. Write notes.md
        if problem.notes:
            notes_path = p_dir / "notes.md"
            notes_lines = [f"# Notes: {problem.title}\n"]
            for note in sorted(problem.notes, key=lambda n: n.created_at):
                notes_lines.append(f"### [{note.note_type.value}] - `{note.created_at.strftime('%Y-%m-%d %H:%M:%S')}`")
                notes_lines.append(f"{note.content}\n")
            notes_path.write_text("\n".join(notes_lines), encoding="utf-8")

        # 5. Write metadata.json
        meta_path = p_dir / "metadata.json"
        meta_data = problem.model_dump(mode="json")
        meta_path.write_text(json.dumps(meta_data, indent=2), encoding="utf-8")

        return problem

    def get_by_id(self, problem_id: str) -> Problem | None:
        """Find problem by ID by scanning metadata.json files."""
        for p_dir in self.root_dir.iterdir():
            if p_dir.is_dir():
                meta_file = p_dir / "metadata.json"
                if meta_file.exists():
                    try:
                        data = json.loads(meta_file.read_text(encoding="utf-8"))
                        if data.get("id") == problem_id:
                            return Problem.model_validate(data)
                    except Exception:
                        continue
        return None

    def get_by_slug(self, slug: str) -> Problem | None:
        """Find problem by slug directory."""
        p_dir = self.root_dir / slug
        meta_file = p_dir / "metadata.json"
        if meta_file.exists():
            try:
                data = json.loads(meta_file.read_text(encoding="utf-8"))
                return Problem.model_validate(data)
            except Exception:
                pass
        return None

    def list_all(self) -> Sequence[Problem]:
        """List all problems stored on filesystem."""
        problems: list[Problem] = []
        if not self.root_dir.exists():
            return problems

        for p_dir in sorted(self.root_dir.iterdir()):
            if p_dir.is_dir():
                meta_file = p_dir / "metadata.json"
                if meta_file.exists():
                    try:
                        data = json.loads(meta_file.read_text(encoding="utf-8"))
                        problems.append(Problem.model_validate(data))
                    except Exception:
                        continue
        return problems

    def delete(self, problem_id: str) -> bool:
        """Delete problem folder from filesystem."""
        prob = self.get_by_id(problem_id)
        if not prob:
            return False
        p_dir = self.root_dir / prob.slug
        if p_dir.exists():
            for child in p_dir.glob("*"):
                if child.is_file():
                    child.unlink()
            p_dir.rmdir()
            return True
        return False

    # SubmissionRepository methods implementation
    def save_submission(self, submission: Submission) -> Submission:
        """Save submission via problem updating."""
        prob = self.get_by_id(submission.problem_id)
        if prob:
            # find or attach attempt
            matched_attempt = None
            for attempt in prob.attempts:
                if submission.attempt_id and attempt.id == submission.attempt_id:
                    matched_attempt = attempt
                    break
            if not matched_attempt:
                if prob.attempts:
                    matched_attempt = prob.attempts[-1]
                else:
                    matched_attempt = Attempt(
                        problem_id=prob.id,
                        attempt_number=1,
                        status=submission.status,
                    )
                    prob.attempts.append(matched_attempt)

            # check duplicate by hash
            existing_hashes = {s.submission_hash for s in matched_attempt.submissions if s.submission_hash}
            if submission.submission_hash not in existing_hashes:
                matched_attempt.submissions.append(submission)
                if submission.status == SubmissionStatus.ACCEPTED:
                    matched_attempt.status = SubmissionStatus.ACCEPTED
                self.save(prob)
        return submission

    def get_by_hash(self, submission_hash: str) -> Submission | None:
        """Search submission by hash across filesystem metadata."""
        for prob in self.list_all():
            for attempt in prob.attempts:
                for sub in attempt.submissions:
                    if sub.submission_hash == submission_hash:
                        return sub
        return None

    def list_by_problem(self, problem_id: str) -> Sequence[Submission]:
        """Get all submissions for problem."""
        prob = self.get_by_id(problem_id) or self.get_by_slug(problem_id)
        if not prob:
            return []
        subs: list[Submission] = []
        for attempt in prob.attempts:
            subs.extend(attempt.submissions)
        return sorted(subs, key=lambda s: s.submitted_at)

    def list_by_attempt(self, attempt_id: str) -> Sequence[Submission]:
        """Get submissions for a specific attempt."""
        for prob in self.list_all():
            for attempt in prob.attempts:
                if attempt.id == attempt_id:
                    return sorted(attempt.submissions, key=lambda s: s.submitted_at)
        return []

    # AttemptRepository methods
    def save_attempt(self, attempt: Attempt) -> Attempt:
        prob = self.get_by_id(attempt.problem_id)
        if prob:
            # replace or add
            for i, a in enumerate(prob.attempts):
                if a.id == attempt.id:
                    prob.attempts[i] = attempt
                    break
            else:
                prob.attempts.append(attempt)
            self.save(prob)
        return attempt
