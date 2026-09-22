# LeetCode Authenticated Sync Architecture Design

**Document Version:** 1.0  
**Date:** 2026-09-22  
**Project:** CodeMemory  
**Author:** Design Specification

---

## Executive Summary

This document specifies a production-ready authenticated LeetCode synchronization system for CodeMemory that retrieves complete submission history (including source code) while maintaining security, reliability, and user trust. The design extends the existing public sync architecture without replacing it.

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

#### `allUserSubmissions` (Full History)
```graphql
query allUserSubmissions($offset: Int!, $limit: Int!, $lastKey: String) {
  submissionList(offset: $offset, limit: $limit, lastKey: $lastKey) {
    lastKey
    hasNext
    submissions {
      id
      lang
      timestamp
      statusDisplay
      runtime
      memory
      title
      titleSlug
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
  submissionDetail(submissionId: $submissionId) {
    id
    code
    lang
    runtime
    memory
    statusDisplay
    timestamp
    question {
      questionId
      title
      titleSlug
    }
  }
}
```

**Rate Limit Observation**: Community reports suggest ~5-10 requests/second sustained is safe; burst limits unknown ([leetcode-query](https://www.npmjs.com/package/leetcode-query)).

---

## 4. Detailed Design

### 4.1 Credential Management

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
        query submissionList($offset: Int!, $limit: Int!, $lastKey: String) {
            submissionList(offset: $offset, limit: $limit, lastKey: $lastKey) {
                lastKey
                hasNext
                submissions {
                    id
                    lang
                    timestamp
                    statusDisplay
                    runtime
                    memory
                    title
                    titleSlug
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
            submissionDetail(submissionId: $submissionId) {
                id
                code
                lang
                runtime
                memory
                statusDisplay
                timestamp
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
        
        if not data or "submissionDetail" not in data:
            return None
        
        detail = data["submissionDetail"]
        if not isinstance(detail, dict):
            return None
        
        question = detail.get("question", {})
        if not isinstance(question, dict):
            question = {}
        
        return {
            "submission_id": detail.get("id"),
            "code": detail.get("code", ""),
            "language": detail.get("lang", "Unknown"),
            "runtime": detail.get("runtime"),
            "memory": detail.get("memory"),
            "status": detail.get("statusDisplay", "Unknown"),
            "timestamp": detail.get("timestamp"),
            "title": question.get("title", ""),
            "title_slug": question.get("titleSlug", ""),
            "question_id": question.get("questionId")
        }
```

---

### 4.3 Sync Orchestration

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

---

**End of Document**