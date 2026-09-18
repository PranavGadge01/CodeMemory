"""Knowledge exporter generating Git-friendly Markdown, code, and JSON metadata files."""

from pathlib import Path

from codememory.domain.models import Problem
from codememory.storage.fs_repository import FilesystemStorage


class KnowledgeExporter:
    """Exporter generating clean human-readable Markdown files for GitHub/Git committing."""

    def __init__(self, output_dir: str | Path = "knowledge"):
        self.fs_storage = FilesystemStorage(root_dir=output_dir)

    def export_problem(self, problem: Problem) -> Path:
        """Export a single problem into knowledge/<slug>/ structure."""
        self.fs_storage.save(problem)
        return self.fs_storage.root_dir / problem.slug

    def export_all(self, problems: list[Problem]) -> list[Path]:
        """Export a sequence of problems into knowledge base."""
        exported_paths: list[Path] = []
        for problem in problems:
            path = self.export_problem(problem)
            exported_paths.append(path)
        return exported_paths
