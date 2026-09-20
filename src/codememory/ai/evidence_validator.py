"""Evidence provenance validator for the grounded insight pipeline.

Enforces the concrete invariant:

    set(interpretation.evidence_refs) ⊆ evidence.all_evidence_ids()

This module does NOT attempt to prove that every sentence in a
natural-language narrative is factually grounded — that is not reliably
enforceable with this architecture.  The enforceable contract is
reference-set containment: every evidence_ref the provider claims to have
used must correspond to an actual evidence item in the bundle.
"""

from __future__ import annotations

from codememory.ai.evidence_models import InsightEvidence
from codememory.ai.providers.base_provider import InterpretationResult
from codememory.domain.exceptions import CodeMemoryError


class EvidenceValidationError(CodeMemoryError):
    """Raised when an InterpretationResult references evidence IDs not present in the evidence bundle."""

    def __init__(self, invalid_refs: set[str]):
        self.invalid_refs = invalid_refs
        refs_str = ", ".join(sorted(invalid_refs))
        super().__init__(
            f"InterpretationResult references {len(invalid_refs)} evidence ID(s) "
            f"not present in the evidence bundle: {refs_str}"
        )


class EvidenceValidator:
    """Validates that provider interpretations only reference existing evidence.

    The single enforced invariant is::

        set(interpretation.evidence_refs) ⊆ evidence.all_evidence_ids()

    This guarantees that every claim of grounding traces back to an actual
    deterministic evidence item.  It does not attempt NLP-level verification
    of narrative content.
    """

    @staticmethod
    def validate(
        evidence: InsightEvidence,
        interpretation: InterpretationResult,
    ) -> None:
        """Validate that all ``evidence_refs`` exist in the evidence bundle.

        Raises:
            EvidenceValidationError: if any ref in
                ``interpretation.evidence_refs`` is not in
                ``evidence.all_evidence_ids()``.
        """
        valid_ids = evidence.all_evidence_ids()
        ref_set = set(interpretation.evidence_refs)
        invalid = ref_set - valid_ids
        if invalid:
            raise EvidenceValidationError(invalid)
