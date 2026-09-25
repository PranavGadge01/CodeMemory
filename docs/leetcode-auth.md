# LeetCode Authenticated Sync Architecture Design

**Document Version:** 1.0  
**Date:** 2026-09-22  
**Project:** CodeMemory  
**Author:** Design Specification

---

## Executive Summary

This document specifies a production-ready authenticated LeetCode synchronization system for CodeMemory that retrieves complete submission history (including source code) while maintaining security, reliability, and user trust. The design extends the existing public sync architecture without replacing it.

> **Implementation status note (2026-09-25):** This document began as a design proposal. Sections 4–5 retain some proposal-era examples and rollout planning; the implementation-status table at the end is authoritative for what the repository currently does. The GraphQL examples below have been corrected to the current client request shape.

---

## 1. Problem Statement

### Current Limitations
- **Public API constraint**: `recentAcSubmissions` returns only ~20 recent accepted submissions
- **No source code**: Public query returns metadata only (no code)
- **No failed submissions**: Only accepted submissions visible
- **Incomplete history**: Users with 1000+ submissions cannot import full dataset

### User Impact
- **Incomplete knowledge base**: CodeMemory cannot analyze full problem-solving evolution
- **Missing failure analysis**: TLE/WA attempts not captured for learning
- **Limited revision engine**: Cannot build spaced repetition from complete history
- **Degraded semantic search**: Small corpus reduces similarity matching quality

---

## 2. Solution Overview

### Architecture Principle
**Dual-Mode Sync**: Keep existing public sync as default; add authenticated full-history sync as opt-in capability.

```
┌─────────────────────────────────────────┐
│         LeetCode Sync Manager           │
├─────────────────────────────────────────┤
│                                         │
│  Mode 1: Public Sync (Default)         │
│  ├─ No credentials required            │
│  ├─ Recent 20 accepted submissions     │
│  ├─ Metadata only                      │
│  └─ Safe, stable, always available     │
│                                         │
│  Mode 2: Authenticated Sync (Opt-In)   │
│  ├─ LEETCODE_SESSION + csrftoken       │
│  ├─ Complete submission history        │
│  ├─ Source code retrieval              │
│  ├─ Failed attempts (TLE, WA, MLE)     │
│  └─ Paginated deep scan                │
│                                         │
└─────────────────────────────────────────┘
```

---

## 3. Research Findings

### 3.1 Authentication Mechanism

Based on community implementations ([leetcode-graphql-queries](https://github.com/akarsh1995/leetcode-graphql-queries), [python-leetcode](https://github.com/fspv/python-leetcode)), LeetCode's authenticated GraphQL requires:

**Required Headers:**
```python
{
    "Cookie": "LEETCODE_SESSION=<token>; csrftoken=<token>",
    "x-csrftoken": "<token>",
    "Referer": "https://leetcode.com",
    "Content-Type": "application/json"
}
```

**Critical Discovery**: Cloudflare protection may also require `cf_clearance` token in certain network environments ([source](https://gist.github.com/satvik-1203/0ba390511610f3ccee81fc6d074333cd)).

### 3.2 Available GraphQL Queries

Research identifies these authenticated endpoints:

#### `submissionList` (Full History — current request shape)
```graphql
query submissionList($limit: Int!, $offset: Int!, $lastKey: String) {
  submissionList(limit: $limit, offset: $offset, lastKey: $lastKey) {
    lastKey
    hasNext
    submissions {
      id
      title
      titleSlug
      timestamp
      statusDisplay
      lang
      __typename
    }
  }
}
```

**Pagination Pattern:**
- Initial: `offset=0, limit=100, lastKey=null`
- Next: `offset=100, limit=100, lastKey=<from_previous_response>`
- Terminal: `hasNext=false`

#### `submissionDetails` (Code Retrieval)
```graphql
query submissionDetails($submissionId: Int!) {
  submissionDetails(submissionId: $submissionId) {
    code
    runtime
    memory
    timestamp
    statusCode
    lang {
      name
      verboseName
    }
    question {
      questionId
      title
      titleSlug
    }
  }
}
```

The client parses the response object at `data.submissionDetails`; `lang` is
normalized from `verboseName` (falling back to `name`), and the request's
submission ID is retained because the detail response does not request an ID
field. The tests use a mocked response matching this shape. LeetCode's schema
error identified `submissionDetails` as the replacement for `submissionDetail`;
the full field structure has not yet been verified by a successful live detail
request in this environment.

**Rate Limit Observation**: Community reports suggest ~5-10 requests/second sustained is safe; burst limits unknown ([leetcode-query](https://www.npmjs.com/package/leetcode-query)).

---

## 4. Detailed Design

### 4.0 Actual Runtime Architecture

The implemented authenticated path is:

```text
Next.js settings / account UI
    ↓
FastAPI authenticated LeetCode routes
    ↓
LeetCodeAccountService
    ↓
AuthenticatedSyncOrchestrator
    ↓
AuthenticatedLeetCodeClient
    ↓
LeetCode GraphQL
```

The authenticated sync is implemented in the Next.js + FastAPI application.
The Streamlit page described later in this original proposal is not part of the
current application.

### 4.1 Credential Management

The storage tree and Python snippet in this subsection are proposal-era examples,
not the current on-disk layout or implementation. See the implementation-status
table for the actual per-account encrypted keyring/file behavior.

#### Storage Location
```
data/accounts/<username>/
├── credentials.enc          # Encrypted session tokens
├── sync_state.json         # Last sync checkpoint
└── sync_log.jsonl          # Audit trail
```

#### Encryption Strategy
```python
from cryptography.fernet import Fernet
import keyring  # OS-native secure storage

class CredentialVault:
    """Secure storage for LeetCode session credentials."""
    
    def __init__(self, username: str):
        self.username = username
        # Master key stored in OS keyring (Windows Credential Manager / macOS Keychain)
        self.master_key = self._get_or_create_master_key()
        self.cipher = Fernet(self.master_key)
    
    def _get_or_create_master_key(self) -> bytes:
        key = keyring.get_password("CodeMemory", "vault_key")
        if not key:
            key = Fernet.generate_key().decode()
            keyring.set_password("CodeMemory", "vault_key", key)
        return key.encode()
    
    def store_session(self, leetcode_session: str, csrf_token: str) -> None:
        """Encrypt and persist session credentials."""
        payload = json.dumps({
            "leetcode_session": leetcode_session,
            "csrf_token": csrf_token,
            "stored_at": datetime.now(timezone.utc).isoformat()
        })
        encrypted = self.cipher.encrypt(payload.encode())
        path = self._credentials_path()
        path.write_bytes(encrypted)
        path.chmod(0o600)  # Owner read/write only
    
    def retrieve_session(self) -> Optional[Dict[str, str]]:
        """Decrypt and return stored credentials."""
        path = self._credentials_path()
        if not path.exists():
            return None
        encrypted = path.read_bytes()
        decrypted = self.cipher.decrypt(encrypted).decode()
        return json.loads(decrypted)
    
    def validate_session(self) -> bool:
        """Check if stored session is still valid."""
        creds = self.retrieve_session()
        if not creds:
            return False
        # Test with lightweight profile query
        client = AuthenticatedLeetCodeClient(
            session=creds["leetcode_session"],
            csrf=creds["csrf_token"]
        )
        profile = client.fetch_user_profile(self.username)
        return profile is not None
```

**Security Properties:**
- Master key in OS native vault (survives app uninstall)
- Session tokens encrypted at rest with Fernet (AES-128-CBC + HMAC)
- File permissions restricted to owner
- No plaintext credentials in logs or UI

#### User Consent Flow
```
User clicks "Sync Full History"
       ↓
[First Time Only]
       ↓
Educational Modal:
┌────────────────────────────────────────────────┐
│  Full History Sync                             │
├────────────────────────────────────────────────┤
│  This requires your LeetCode session cookie.   │
│                                                │
│  ✓ Stored encrypted on your local machine     │
│  ✓ Never sent to external servers             │
│  ✓ Used only for LeetCode.com API calls       │
│  ✓ You can revoke anytime                     │
│                                                │
│  How to get your session cookie:              │
│  1. Open LeetCode in browser (logged in)      │
│  2. DevTools → Application → Cookies          │
│  3. Copy LEETCODE_SESSION value               │
│  4. Copy csrftoken value                      │
│                                                │
│  [Video Tutorial] [Cancel] [I Understand]     │
└────────────────────────────────────────────────┘
       ↓
Input Form (masked fields)
       ↓
Validation Test (profile fetch)
       ↓
Success → Store encrypted → Start sync
```

---

### 4.2 Authenticated Client Extension

The following client listing is an original design sketch, not a copy of the
current source file. Its query examples above have been corrected, but the
current implementation lives in `src/codememory/connectors/leetcode/authenticated_client.py`.

```python
# src/codememory/connectors/leetcode/authenticated_client.py

from typing import Optional, Dict, Any, List
import logging
from codememory.connectors.leetcode.client import LeetCodeClient
from codememory.connectors.leetcode.models import LeetCodeSubmissionRaw

logger = logging.getLogger(__name__)

class AuthenticatedLeetCodeClient(LeetCodeClient):
    """Extended client supporting authenticated full-history operations."""
    
    def __init__(
        self,
        session: str,
        csrf_token: str,
        **kwargs
    ):
        super().__init__(session_cookie=session, **kwargs)
        self.csrf_token = csrf_token
        self._authenticated = True
    
    def _headers(self) -> Dict[str, str]:
        """Override to include CSRF token for authenticated requests."""
        headers = super()._headers()
        if self._authenticated and self.csrf_token:
            headers["x-csrftoken"] = self.csrf_token
            # Update cookie format for authenticated requests
            headers["Cookie"] = (
                f"LEETCODE_SESSION={self.session_cookie}; "
                f"csrftoken={self.csrf_token}"
            )
        return headers
    
    def fetch_all_submissions_paginated(
        self,
        username: str,
        batch_size: int = 100,
        progress_callback: Optional[callable] = None
    ) -> List[LeetCodeSubmissionRaw]:
        """Fetch complete submission history with pagination.
        
        Args:
            username: LeetCode username
            batch_size: Submissions per page (max 100)
            progress_callback: Optional callback(current, total, batch)
        
        Returns:
            Complete list of all submissions (includes failed attempts)
        """
        all_submissions: List[LeetCodeSubmissionRaw] = []
        offset = 0
        last_key = None
        has_next = True
        page = 0
        
        query = """
        query submissionList($limit: Int!, $offset: Int!, $lastKey: String) {
            submissionList(limit: $limit, offset: $offset, lastKey: $lastKey) {
                lastKey
                hasNext
                submissions {
                    id
                    title
                    titleSlug
                    timestamp
                    statusDisplay
                    lang
                    __typename
                }
            }
        }
        """
        
        while has_next:
            page += 1
            variables = {
                "offset": offset,
                "limit": batch_size,
                "lastKey": last_key
            }
            
            logger.info(
                f"Fetching page {page} (offset={offset}, lastKey={last_key})"
            )
            
            result = self.execute_query(query, variables)
            data = self._graphql_data(result)
            
            if not data or "submissionList" not in data:
                logger.warning(f"No submissionList in response at offset {offset}")
                break
            
            submission_list = data["submissionList"]
            if not isinstance(submission_list, dict):
                logger.warning(f"Malformed submissionList at offset {offset}")
                break
            
            # Parse submissions in this page
            raw_items = submission_list.get("submissions", [])
            if not isinstance(raw_items, list):
                logger.warning(f"Malformed submissions array at offset {offset}")
                break
            
            batch_submissions = []
            for item in raw_items:
                if not isinstance(item, dict):
                    continue
                try:
                    batch_submissions.append(
                        LeetCodeSubmissionRaw(
                            id=item.get("id"),
                            submission_id=item.get("id"),
                            title=item.get("title", ""),
                            title_slug=item.get("titleSlug"),
                            language=item.get("lang", "Unknown"),
                            status=item.get("statusDisplay", "Unknown"),
                            timestamp=item.get("timestamp"),
                            runtime=item.get("runtime"),
                            memory=item.get("memory")
                        )
                    )
                except Exception as e:
                    logger.warning(f"Skipping malformed submission: {e}")
            
            all_submissions.extend(batch_submissions)
            
            # Check pagination
            has_next = submission_list.get("hasNext", False)
            last_key = submission_list.get("lastKey")
            offset += batch_size
            
            if progress_callback:
                progress_callback(len(all_submissions), None, len(batch_submissions))
            
            # Rate limiting: sleep between pages
            if has_next:
                self._sleep(0.5)  # 500ms between requests
        
        logger.info(f"Fetched {len(all_submissions)} total submissions in {page} pages")
        return all_submissions
    
    def fetch_submission_code(self, submission_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve source code for a specific submission.
        
        Args:
            submission_id: Numeric submission ID
        
        Returns:
            Dict with code, lang, runtime, memory, status
        """
        query = """
        query submissionDetails($submissionId: Int!) {
            submissionDetails(submissionId: $submissionId) {
                code
                runtime
                memory
                timestamp
                statusCode
                lang {
                    name
                    verboseName
                }
                question {
                    questionId
                    title
                    titleSlug
                }
            }
        }
        """
        
        result = self.execute_query(query, {"submissionId": submission_id})
        data = self._graphql_data(result)
        
        if not data or "submissionDetails" not in data:
            return None

        detail = data["submissionDetails"]
        if not isinstance(detail, dict):
            return None
        
        question = detail.get("question", {})
        if not isinstance(question, dict):
            question = {}
        
        return {
            "submission_id": str(submission_id),
            "code": detail.get("code", ""),
            "language": (detail.get("lang") or {}).get("verboseName") or (detail.get("lang") or {}).get("name"),
            "runtime": detail.get("runtime"),
            "memory": detail.get("memory"),
            "status": detail.get("statusCode"),
            "timestamp": detail.get("timestamp"),
            "title": question.get("title", ""),
            "title_slug": question.get("titleSlug", ""),
            "question_id": question.get("questionId")
        }
```

---

### 4.3 Sync Orchestration

The following orchestration listing is proposal-era pseudocode. The current
orchestrator processes one page at a time and persists cursors in account
connection metadata, as summarized in the status table.

```python
# src/codememory/connectors/leetcode/authenticated_sync.py

from typing import Optional
from datetime import datetime, timezone
import logging
from codememory.connectors.leetcode.authenticated_client import AuthenticatedLeetCodeClient
from codememory.connectors.account.models import SyncStatus, SyncState
from codememory.core.service import CodeMemoryService

logger = logging.getLogger(__name__)

class AuthenticatedSyncOrchestrator:
    """Manages authenticated full-history sync with checkpointing."""
    
    def __init__(
        self,
        service: CodeMemoryService,
        client: AuthenticatedLeetCodeClient,
        username: str
    ):
        self.service = service
        self.client = client
        self.username = username
        self.checkpoint_file = f"data/accounts/{username}/sync_checkpoint.json"
    
    def sync_full_history(
        self,
        fetch_code: bool = True,
        progress_callback: Optional[callable] = None
    ) -> SyncStatus:
        """Execute complete authenticated sync with progress tracking."""
        
        status = SyncStatus(
            started_at=datetime.now(timezone.utc),
            status=SyncState.RUNNING
        )
        
        try:
            # Phase 1: Fetch all submission metadata
            logger.info(f"Phase 1: Fetching submission metadata for {self.username}")
            submissions = self.client.fetch_all_submissions_paginated(
                username=self.username,
                progress_callback=progress_callback
            )
            status.records_discovered = len(submissions)
            
            # Phase 2: Process metadata (deduplicate, normalize, store)
            logger.info(f"Phase 2: Processing {len(submissions)} submissions")
            for idx, raw_sub in enumerate(submissions):
                try:
                    # Check if already exists (by submission hash)
                    existing = self.service.find_submission_by_hash(
                        raw_sub.compute_hash()
                    )
                    
                    if existing:
                        status.records_skipped += 1
                        continue
                    
                    # Import metadata
                    self.service.import_submission_metadata(raw_sub, self.username)
                    status.records_added += 1
                    
                    if progress_callback:
                        progress_callback(idx + 1, len(submissions), None)
                    
                except Exception as e:
                    logger.warning(f"Failed to process submission {raw_sub.id}: {e}")
                    status.records_failed += 1
            
            # Phase 3: Fetch source code (batched with rate limiting)
            if fetch_code:
                logger.info(f"Phase 3: Fetching source code for accepted submissions")
                accepted = [s for s in submissions if s.status == "Accepted"]
                code_fetched = 0
                
                for idx, sub in enumerate(accepted):
                    try:
                        code_data = self.client.fetch_submission_code(
                            int(sub.submission_id)
                        )
                        
                        if code_data and code_data.get("code"):
                            self.service.update_submission_code(
                                submission_id=sub.submission_id,
                                code=code_data["code"],
                                source_account=self.username
                            )
                            code_fetched += 1
                        
                        # Rate limit: 2 requests/second
                        self.client._sleep(0.5)
                        
                        if progress_callback:
                            progress_callback(idx + 1, len(accepted), code_fetched)
                    
                    except Exception as e:
                        logger.warning(f"Failed to fetch code for {sub.id}: {e}")
                
                status.details["code_fetched"] = code_fetched
            
            # Success
            status.status = SyncState.SUCCESS
            status.finished_at = datetime.now(timezone.utc)
            logger.info(
                f"Authenticated sync completed: "
                f"{status.records_added} added, "
                f"{status.records_skipped} skipped, "
                f"{status.records_failed} failed"
            )
        
        except Exception as e:
            status.status = SyncState.FAILED
            status.error_message = str(e)
            status.finished_at = datetime.now(timezone.utc)
            logger.error(f"Authenticated sync failed: {e}", exc_info=True)
        
        return status
```

---

### 4.4 UI Integration

The Streamlit page below was proposed but not implemented. The current settings
and account UI is Next.js and calls the FastAPI routes described in section 4.0.

#### Streamlit Page: `app/pages/account_sync.py`

```python
import streamlit as st
from codememory.connectors.leetcode.authenticated_client import AuthenticatedLeetCodeClient
from codememory.connectors.leetcode.authenticated_sync import AuthenticatedSyncOrchestrator
from codememory.connectors.account.credential_vault import CredentialVault

def render_authenticated_sync_page():
    st.title("🔒 Full History Sync")
    
    username = st.text_input("LeetCode Username", key="auth_username")
    
    if not username:
        st.info("Enter your username to begin")
        return
    
    vault = CredentialVault(username)
    
    # Check if credentials exist
    if vault.retrieve_session():
        st.success("✓ Credentials stored securely")
        
        if st.button("🔄 Sync Full History"):
            run_authenticated_sync(username, vault)
        
        if st.button("🗑️ Revoke Credentials"):
            vault.delete_session()
            st.success("Credentials removed")
            st.rerun()
    
    else:
        # First-time setup
        st.warning("⚠️ Full history sync requires authentication")
        
        with st.expander("ℹ️ Why do you need my session cookie?"):
            st.markdown("""
            LeetCode's public API only returns your 20 most recent submissions.
            
            To import your **complete history** (including failed attempts and source code),
            CodeMemory needs your authenticated browser session.
            
            **Security guarantee:**
            - Stored encrypted on your local machine only
            - Never transmitted to external servers
            - Used exclusively for LeetCode GraphQL API calls
            - You can revoke access anytime
            """)
        
        with st.form("credentials_form"):
            st.markdown("### How to get your session tokens")
            st.markdown("""
            1. Open [leetcode.com](https://leetcode.com) (logged in)
            2. Press F12 → **Application** tab
            3. Expand **Cookies** → leetcode.com
            4. Copy the values below:
            """)
            
            leetcode_session = st.text_input(
                "LEETCODE_SESSION",
                type="password",
                help="Long hexadecimal string"
            )
            csrf_token = st.text_input(
                "csrftoken",
                type="password",
                help="Shorter token"
            )
            
            consent = st.checkbox(
                "I understand these credentials are stored encrypted locally"
            )
            
            submitted = st.form_submit_button("🔐 Save & Validate")
            
            if submitted:
                if not consent:
                    st.error("Please confirm understanding")
                elif not leetcode_session or not csrf_token:
                    st.error("Both tokens required")
                else:
                    validate_and_store(username, leetcode_session, csrf_token, vault)

def validate_and_store(username, session, csrf, vault):
    with st.spinner("Validating credentials..."):
        client = AuthenticatedLeetCodeClient(session=session, csrf_token=csrf)
        profile = client.fetch_user_profile(username)
        
        if profile:
            vault.store_session(session, csrf)
            st.success("✓ Credentials validated and stored securely")
            st.rerun()
        else:
            st.error("❌ Invalid credentials or wrong username")

def run_authenticated_sync(username, vault):
    creds = vault.retrieve_session()
    client = AuthenticatedLeetCodeClient(
        session=creds["leetcode_session"],
        csrf_token=creds["csrf_token"]
    )
    
    service = st.session_state.get("service")  # CodeMemoryService instance
    orchestrator = AuthenticatedSyncOrchestrator(service, client, username)
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    def progress_callback(current, total, batch):
        if total:
            progress_bar.progress(current / total)
            status_text.text(f"Processing {current}/{total} submissions...")
    
    with st.spinner("Syncing full history..."):
        sync_result = orchestrator.sync_full_history(
            fetch_code=True,
            progress_callback=progress_callback
        )
    
    if sync_result.status == "Success":
        st.success(f"""
        ✅ Sync complete!
        - {sync_result.records_added} new submissions imported
        - {sync_result.records_skipped} already existed
        - {sync_result.details.get('code_fetched', 0)} source codes retrieved
        """)
    else:
        st.error(f"Sync failed: {sync_result.error_message}")
```

---

## 5. Implementation Plan

This checklist is retained as the original plan snapshot; completion status is
tracked in the implementation-status table below.

### Phase 1: Foundation (Week 1)
- [ ] Create `authenticated_client.py` extending `LeetCodeClient`
- [ ] Implement `CredentialVault` with OS keyring integration
- [ ] Add `AuthenticatedLeetCodeClient.fetch_all_submissions_paginated()`
- [ ] Unit tests with mocked responses

### Phase 2: Sync Orchestration (Week 2)
- [ ] Build `AuthenticatedSyncOrchestrator` with checkpointing
- [ ] Implement code retrieval phase with rate limiting
- [ ] Add resume-from-checkpoint logic
- [ ] Integration tests with test account

### Phase 3: UI Integration (Week 3)
- [ ] Create Streamlit authenticated sync page
- [ ] Educational modal + consent flow
- [ ] Progress tracking UI components
- [ ] Credential revocation workflow

### Phase 4: Testing & Polish (Week 4)
- [ ] Live testing with 1000+ submission accounts
- [ ] Rate limit boundary testing
- [ ] Error recovery scenarios
- [ ] Documentation + video tutorial

### Phase 5: Rollout (Week 5)
- [ ] Beta release to 5-10 users
- [ ] Monitor sync success rates
- [ ] Gather feedback on UX
- [ ] Production release

---

## 6. Risk Mitigation

### Risk: Session Expiration
**Probability:** High  
**Impact:** Medium

**Mitigation:**
- Auto-validate session before each sync
- Prompt user to refresh if expired
- Store expiration timestamp from LeetCode response

### Risk: Rate Limiting
**Probability:** Medium  
**Impact:** High (sync failure)

**Mitigation:**
- Implement exponential backoff with `Retry-After` header
- Default 500ms between requests (conservative)
- Checkpoint every 100 submissions (resume on 429)
- CLI flag `--rate-limit-delay` for tuning

### Risk: Credential Theft
**Probability:** Low  
**Impact:** Critical

**Mitigation:**
- Fernet encryption at rest (AES-128 + HMAC)
- Master key in OS secure storage (not in code/env/files)
- File permissions 0600 (owner read/write only)
- No credentials in logs/error messages/UI

### Risk: LeetCode API Changes
**Probability:** Medium  
**Impact:** High (sync breaks)

**Mitigation:**
- Fallback to public sync on GraphQL errors
- Version detection via response schema
- Community monitoring (GitHub watch on query repos)
- Graceful degradation messaging

---

## 7. Success Metrics

### Technical KPIs
- **Sync success rate**: >95% for accounts with valid credentials
- **Code retrieval rate**: >98% for accepted submissions
- **Average sync time**: <2 minutes per 100 submissions
- **Failure recovery**: Resume from checkpoint within 3 retries

### User Experience KPIs
- **Credential setup time**: <90 seconds median
- **Consent flow completion**: >80% of users who start
- **Support tickets re: sync errors**: <5% of users

---

## 8. Alternatives Considered

### Alternative 1: Browser Extension
**Rejected**: Higher development complexity, distribution challenges, platform-specific code.

### Alternative 2: OAuth Flow
**Rejected**: LeetCode does not offer public OAuth; would require unofficial reverse-engineering.

### Alternative 3: Scraping
**Rejected**: Violates LeetCode ToS, fragile to UI changes, unethical.

---

## 9. Future Enhancements

1. **Auto-refresh sessions**: Detect expiration, guide user through renewal
2. **Multi-account orchestration**: Sync multiple LeetCode accounts in parallel
3. **Incremental sync**: Delta sync from `last_sync_at` timestamp
4. **Contest history**: Extend to fetch contest performance data
5. **LeetCode CN support**: Separate GraphQL endpoint, different auth flow

---

## 10. References

- [leetcode-graphql-queries GitHub](https://github.com/akarsh1995/leetcode-graphql-queries)
- [python-leetcode API Client](https://github.com/fspv/python-leetcode)
- [leetcode-query npm package](https://www.npmjs.com/package/leetcode-query)
- [@leetnotion/leetcode-api](https://www.npmjs.com/package/@leetnotion/leetcode-api)
- [LeetCode Discord Reporter](https://github.com/Harshith1702/leetcode-discord-reporter)

## Implementation Status — September 2026

This table reflects repository code and tests, not the original proposal. Live
status is reported separately from mocked/unit-test evidence. GraphQL field and
response details describe what the client currently sends/parses. The current
`submissionDetails` request returned source details during live verification on
2026-09-25.

| Requirement | Status | Actual Implementation | Notes |
|---|---|---|---|
| Public sync | ✅ IMPLEMENTED | `LeetCodeSyncEngine` uses the unauthenticated public client and recent accepted-submission window. | Remains independently available. |
| Authenticated sync | ✅ IMPLEMENTED | FastAPI → `LeetCodeAccountService` → `AuthenticatedSyncOrchestrator` → authenticated GraphQL client. | A second full-history sync completed through the live API. |
| Credentials | ✅ IMPLEMENTED | `LEETCODE_SESSION` and `csrftoken` are held by the backend client and sent only in authenticated request headers. | They are not placed in URLs or API response models. |
| Encryption | ⚠️ PARTIAL | Credential payloads are Fernet-encrypted before keyring or JSON-file persistence; master key is account-scoped in OS keyring. | Encrypted-file fallback works only when the Fernet key is available. No plaintext fallback exists. This audit did not independently verify restart retrieval/revoke in the normal Windows user session. |
| Session validation | ✅ IMPLEMENTED | Save and validate issue a one-item authenticated `submissionList` request; invalid/malformed page responses fail validation. | The stored session returned valid through the live API on 2026-09-25. |
| Revocation | ✅ IMPLEMENTED | Deletes the account-scoped keyring item and encrypted file on a best-effort basis. | A keyring deletion error is logged; file cleanup is still attempted. |
| Full history | ✅ IMPLEMENTED | `submissionList(limit, offset, lastKey)` reads the session user's history page-by-page. | No username argument; no accepted-only history filter. |
| Failed submissions | ✅ IMPLEMENTED | History parsing preserves each returned status; only accepted records trigger code detail fetches. | Verified by mocked sync tests. |
| Source code | ✅ IMPLEMENTED | Accepted IDs are passed as integer `submissionId` to `submissionDetails`; parser reads code, language object, runtime, memory, status code, timestamp, and question fields. | The live second sync fetched 34 source-detail responses with `code_failed=0`; stored code was present on 34 accepted records. Current data contained Java only. |
| Pagination | ✅ IMPLEMENTED | Uses `limit=100`, increasing `offset`, `lastKey`, and `hasNext`. | Transport and orchestrator tests cover multiple pages. |
| Checkpointing | ✅ IMPLEMENTED | Last key and associated username are stored in connection metadata after pages with a next cursor. | Checkpoint clears after successful completion; history page failures raise instead of becoming empty final pages. |
| Resume | ✅ IMPLEMENTED | Orchestrator starts from the saved key and validates checkpoint username against active connection. | Covered by failure/resume tests. |
| Deduplication | ✅ IMPLEMENTED | Compares account provenance plus submission hash and external submission ID before storage. | Live second sync discovered 60, added 0, skipped 60, and failed 0; stored total remained 67. |
| Multi-account isolation | ⚠️ PARTIAL | Credential vault keys and stored submission provenance are account-scoped; checkpoint records its username. | Account service retains one active LeetCode connection at a time; parallel synchronization is not implemented. Public submission responses omit source-account provenance, so it was not independently audited through the API. |
| Rate limiting | ⚠️ PARTIAL | Pages are separated by a delay and transport retries are bounded with backoff/`Retry-After` handling. | Detail requests for accepted submissions have no separate inter-request delay; monitor live behavior before large archives. |
| Error handling | ✅ IMPLEMENTED | History failures fail the sync; detail failures increment `code_failed` while retaining successfully stored history metadata. | HTTP errors have bounded credential-redacted diagnostics. |
| FastAPI | ✅ IMPLEMENTED | Authenticated store, validate, sync, and revoke routes expose safe response models; failed sync returns HTTP 502. | Route behavior is covered by API tests. |
| Next.js | ⚠️ PARTIAL | LeetCode account status, connect, authenticated store/validate/sync/revoke, and sync results use FastAPI. | Other platform cards remain preview-only. Embedded browser access to the local API was blocked, so the UI flow was not independently verified live. |
| Tests | ✅ IMPLEMENTED | Authenticated, API, network, multi-account, checkpoint, and full-suite tests exist. | Latest full run: 545 passed, 1 deselected, 1 deprecation warning. |
| Live verification | ⚠️ PARTIAL | Stored session validation and a second full-history sync completed via the local API. | Second sync: 60 discovered, 0 added, 60 skipped, 0 failed, 34 code fetched, 0 code failed. First-sync counters were not retained; restart persistence was not verified. |

### Proposal Items Not Implemented

The initial Streamlit page, auto-refreshing sessions, incremental/delta sync,
contest history, LeetCode CN, production/beta rollout, video tutorial, 1000+
account stress testing, parallel multi-account synchronization, automatic
schema-version detection, and community-query monitoring remain proposals or
future work. They are not part of the current authenticated sync.

### Evidence Limitations

The test suite demonstrates request serialization and response parsing using
mocked HTTP responses. During the 2026-09-25 audit, unauthenticated GraphQL
introspection was rejected with HTTP 403. An authenticated `submissionDetails`
request did return code details for 34 accepted submissions, but a single
account and one language do not establish a versioned LeetCode schema contract.
The second sync saw 60 submissions, below the client's 100-item page size, so
that run did not independently verify multiple live history pages. Restart
persistence and first-sync counters were unavailable for independent audit.

---

**End of Document**
