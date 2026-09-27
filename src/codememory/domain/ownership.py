"""Account projections. Canonical aggregates are never replaced by these views."""
from datetime import datetime, timezone
from codememory.domain.models import Problem
from codememory.domain.enums import SubmissionStatus

UNASSIGNED = "__codememory_legacy_unassigned__"


def inferred_owner(submissions):
    owners = {s.source_account for s in submissions}
    if len(owners) == 1:
        owner = next(iter(owners))
        if owner is not None or all(s.source_provider is None for s in submissions):
            return owner
    return UNASSIGNED if submissions else None


def scope_problem(problem: Problem, account: str | None) -> Problem | None:
    """Return private data only for the requested account, including activity."""
    view = problem.model_copy(deep=True)
    view.attempts = []
    for attempt in problem.attempts:
        subs = [s for s in attempt.submissions if (
            s.source_account == account if account is not None
            else s.source_account is None and s.source_provider is None
        )]
        owned = attempt.source_account == account
        if not subs and not (owned and not attempt.submissions):
            continue
        item = attempt.model_copy(deep=True)
        item.submissions = subs
        if not owned:
            item.approach_summary = "Attempt"
            item.reasoning = None
            item.mistakes = []
            item.analysis = None
        if subs:
            item.status = (SubmissionStatus.ACCEPTED if any(s.status == SubmissionStatus.ACCEPTED for s in subs)
                           else max(subs, key=lambda s: s.submitted_at).status)
            # Shared attempt timestamps can reveal another account's activity.
            if not owned:
                item.created_at = min(s.submitted_at for s in subs)
                item.updated_at = max(s.submitted_at for s in subs)
        view.attempts.append(item)
    view.notes = [n for n in view.notes if n.source_account == account]
    view.revision_states = [r for r in view.revision_states if r.source_account == account]
    manual_empty = account is None and not problem.attempts and not problem.notes and not problem.revision_states
    if not (view.attempts or view.notes or view.revision_states or manual_empty):
        return None
    # A shared problem's mutable timestamp must never drive private due state.
    dates = [a.updated_at for a in view.attempts] + [s.submitted_at for a in view.attempts for s in a.submissions]
    dates += [n.created_at for n in view.notes] + [r.last_activity_at for r in view.revision_states]
    view.updated_at = max(dates) if dates else problem.updated_at
    view.created_at = min([s.submitted_at for a in view.attempts for s in a.submissions] or [view.updated_at])
    return view


class AccountStorageView:
    """Read-only adapter for services that historically queried raw storage."""
    def __init__(self, storage, account):
        self.storage, self.account = storage, account

    def list_all(self):
        account = self.account()
        return [view for p in self.storage.list_all() if (view := scope_problem(p, account)) is not None]

    def get_by_id(self, identifier):
        p = self.storage.get_by_id(identifier)
        return scope_problem(p, self.account()) if p else None

    def get_by_slug(self, identifier):
        p = self.storage.get_by_slug(identifier)
        return scope_problem(p, self.account()) if p else None
