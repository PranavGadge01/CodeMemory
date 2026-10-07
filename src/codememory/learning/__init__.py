"""Deterministic learning-profile, candidate-retrieval, and roadmap services.

This package is intentionally LLM-free. It computes an evidence-based
``LearningProfile`` from the user's full submission history, retrieves and
ranks *real* candidate problems, and assembles a gated, deduplicated roadmap.
AI providers are only ever handed the deterministic result to explain.
"""
