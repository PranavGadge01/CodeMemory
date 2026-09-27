"""Isolated real API/storage for browser regression; only LeetCode transport is fake."""
import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock

os.environ['CODEMEMORY_CORS_ORIGINS'] = 'http://127.0.0.1:4174'
from api.app import create_app
from codememory.core.service import CodeMemoryService
from codememory.connectors.account.service import AccountService
from codememory.connectors.leetcode.service import LeetCodeAccountService
from codememory.connectors.leetcode.models import LeetCodeSubmissionRaw
from codememory.domain.models import Problem, Attempt, Submission, ProblemNote
import uvicorn

with tempfile.TemporaryDirectory(prefix='codememory-browser-') as directory:
    base = Path(directory)
    accounts = AccountService(base / 'accounts')
    service = CodeMemoryService(base_dir=base / 'data', knowledge_dir=base / 'knowledge', db_path=base / 'test.duckdb', account_service=accounts)
    client = MagicMock()
    client.fetch_user_profile.side_effect = lambda username: {'username': username, 'real_name': username}
    client.fetch_user_submissions.return_value = []
    client.fetch_problem_details.return_value = None
    service._leetcode_service = LeetCodeAccountService(service, account_service=accounts, client=client)
    vault = MagicMock()
    vault.retrieve.return_value = (None, None)
    service._leetcode_service._credential_vault = lambda account: vault
    old = datetime.now(timezone.utc) - timedelta(days=40)
    problem = Problem(id='shared', slug='two-sum', title='Two Sum', difficulty='Easy', topics=['Array', 'Hash Table'], created_at=old, updated_at=old)
    for index, owner in enumerate(['alice', 'bob']):
        problem.attempts.append(Attempt(id=f'attempt-{owner}', problem_id=problem.id, source_account=owner, attempt_number=index+1, status='Accepted', created_at=old, updated_at=old, submissions=[Submission(id=f'sub-{owner}', problem_id=problem.id, code=f'print("{owner}-private-code")', language='python3', status='Accepted', submitted_at=old, source_account=owner, source_provider='leetcode')]))
        problem.notes.append(ProblemNote(problem_id=problem.id, source_account=owner, content=f'{owner}-private-note', created_at=old))
    service.storage.save(problem)
    try:
        uvicorn.run(create_app(service), host='127.0.0.1', port=8000)
    finally:
        service.close_storage()
