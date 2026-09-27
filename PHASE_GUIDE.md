# CODEMEMORY — MASTER PRODUCTIZATION + WINDOWS RELEASE ROADMAP

You are taking over an existing repository called CodeMemory.

You are NEW to this repository, so before modifying anything, spend time understanding the existing architecture, current implementation, Git state, and recent work. Do NOT assume the repository matches a generic Next.js/Tauri project.

Your job is to take the existing CodeMemory product from its current working state through six structured phases:
1. Fix current app bugs
2. Desktop hardening
3. Product UX / onboarding
4. Public CodeMemory website
5. Windows release/distribution
6. Final cleanup/documentation/regression

IMPORTANT:
- Work incrementally.
- Do not redesign working architecture unnecessarily.
- Do not replace existing working implementations with speculative alternatives.
- Prefer small, explicit changes.
- Preserve existing APIs and behavior unless a change is required.
- Do not silently delete functionality.
- Do not commit automatically unless explicitly instructed.
- After every phase, run the relevant tests/builds and report exactly what changed.
- If you discover a potentially breaking architectural issue, STOP and report it before making a large change.
- Keep generated artifacts out of Git.
- Treat existing production behavior as the baseline.

==================================================
1. CURRENT REPOSITORY CONTEXT
==================================================

CodeMemory is a local-first personal coding-intelligence / learning-memory application centered around LeetCode history.

Current architecture:

Desktop:

    Tauri 2
       |
       +-- static Next.js frontend
       |
       +-- bundled FastAPI sidecar
                |
                +-- DuckDB
                +-- local filesystem
                +-- LeetCode integrations

Development:

    Next.js frontend :3000
          |
          | HTTP
          v
    FastAPI backend :8000
          |
          v
        DuckDB

Backend:

    src/
      api/
      codememory/
        core/
        domain/
        storage/
        analytics/
        memory/
        search/
        revision/
        leetcode/
        graph/
        etc.

Frontend:

    frontend/
      app/
      components/
      lib/
      public/
      src-tauri/

PyInstaller:

    backend/codememory-api.spec

The Tauri production build currently performs:

    npm run build
    npm run sidecar:build
    tauri build

The frontend uses Next.js static export for Tauri.

The current Tauri frontend production architecture is intentionally:

    Tauri
      -> static Next.js export
      -> HTTP -> 127.0.0.1:8000
      -> bundled codememory-api.exe

Do NOT revert this to Next.js SSR for the desktop app.

==================================================
2. IMPORTANT EXISTING FUNCTIONALITY
==================================================

The following functionality already exists and should be preserved:

- FastAPI local API
- DuckDB storage
- Local-first architecture
- LeetCode public username-based sync
- Authenticated LeetCode integration
- Full authenticated submission history
- Failed submissions
- Submission code retrieval
- Credential vault using encrypted credentials + OS keyring
- Multi-account support
- Account-aware submission provenance
- Account-aware dashboard/problems/submissions/analytics/knowledge in most areas
- Search
- Semantic/memory functionality
- Revision functionality
- Tauri Windows application
- Static Next.js frontend
- Bundled PyInstaller FastAPI sidecar
- MSI and NSIS Windows installers

Authenticated LeetCode has already been tested successfully.

A real account currently has:

    71 submissions
    49 unique solved problems

Authenticated sync has successfully discovered all 71 submissions and fetched code for most of them.

Do NOT rebuild the LeetCode integration from scratch.

==================================================
3. IMPORTANT RECENT Tauri WORK
==================================================

The desktop integration went through these milestones:

- Tauri shell
- FastAPI sidecar
- Production sidecar bundling
- Static Next.js export
- Windows MSI/NSIS builds
- Production WebView2 verification
- Frontend -> FastAPI CORS verification
- Dashboard / Problems / Submissions production verification

The static export migration changed submission detail routing.

Old:

    /submissions/[id]

New:

    /submissions?id=<submissionId>

The dynamic route was removed specifically for static export compatibility.

This MUST remain the canonical submission detail route.

==================================================
4. CURRENT KNOWN BUG
==================================================

There is currently a frontend linking bug on the main Submissions page.

Correct behavior:

    /submissions
        |
        | click submission
        v
    /submissions?id=<submissionId>
        |
        v
    submission detail + code

The Problem drawer already uses the correct behavior.

However, clicking a submission from the main Submissions list currently navigates incorrectly toward the Problems page.

Fix this first.

Do NOT modify:
- backend APIs
- submission detail architecture
- Tauri routing architecture
- static export
- Problem drawer behavior

Likely area:

    frontend/components/app/submissions/submissions-browser.tsx

Inspect the actual code before changing it.

==================================================
5. PRODUCT DIRECTION
==================================================

There are now TWO distinct products/interfaces:

A. PUBLIC CODEMEMORY WEBSITE

Purpose:
- Explain CodeMemory
- Show product value
- Show screenshots/features
- Provide downloads
- Eventually provide docs/changelog/releases

B. CODEMEMORY DESKTOP APPLICATION

Purpose:
- Actual coding-memory application
- Connect LeetCode
- Sync submissions
- Analyze history
- Search memory
- Revision
- Analytics

The installed Windows app should NOT behave like a marketing website.

The public website is where marketing/product information belongs.

The desktop application should feel like a real desktop application.

==================================================
6. DESIRED FIRST-LAUNCH EXPERIENCE
==================================================

We want a lightweight first-launch onboarding.

If the user has never configured CodeMemory:

    Launch
      |
      v
    Short CodeMemory intro
      |
      v
    Get Started
      |
      v
    LeetCode username entry
      |
      v
    Public sync
      |
      v
    Dashboard

Example first screen:

    CodeMemory

    Your coding history, remembered.

    CodeMemory connects to your LeetCode profile
    and turns your submission history into a searchable
    coding memory.

    [ Get Started ]

Do NOT create a long multi-page tutorial.

One lightweight intro screen is enough.

Then:

    Connect LeetCode

    Enter your LeetCode username

    [ username ]

    [ Continue ]

After successful setup:

    Dashboard

On subsequent launches:

    Launch
      |
      v
    Dashboard

Do NOT show the marketing homepage again.

The onboarding state must be stored locally.

If no account is connected / no onboarding has been completed:
    show onboarding.

If an account is already configured:
    go directly to the application.

If the user disconnects their only account:
    return them to the appropriate connection/onboarding state.

Do not break authenticated LeetCode functionality.

==================================================
7. PHASE 1 — FIX CURRENT APP BUGS
==================================================

Goal:

Fix current application correctness issues before productization.

Tasks:

1. Fix main Submissions page linking:

    /submissions
      -> /submissions?id=<id>

2. Verify submission detail still loads:
   - metadata
   - status
   - language
   - runtime
   - memory
   - timestamp
   - source account
   - code when available

3. Verify Problem drawer submission links still work.

4. Test major navigation:
   - Dashboard
   - Problems
   - Problem detail
   - Submissions
   - Submission detail
   - Analytics
   - Knowledge
   - Revision
   - Search
   - Settings

5. Do not change unrelated architecture.

Verification:

    npm run typecheck
    npm run build

Run relevant backend tests if backend code was touched.

CHECKPOINT:
Report:
- files changed
- tests
- build result
- remaining issues

Do not proceed to major architectural changes if Phase 1 introduces regressions.

==================================================
8. PHASE 2 — DESKTOP HARDENING
==================================================

This phase is about making the Windows app robust.

--------------------------------
2.1 Multi-account isolation
--------------------------------

Audit and fix account isolation in all user-facing operations.

Previously identified risk areas include:

- semantic search
- SearchService
- semantic_search.py
- revision mark_reviewed
- revision priority
- revision due operations

The invariant must be:

    Active Account A
        ->
        only Account A data is visible/modifiable

    Active Account B
        ->
        only Account B data is visible/modifiable

Raw storage may contain multiple accounts.

User-facing services must respect active account context.

Add regression tests.

Do NOT rely only on frontend filtering.

Isolation must exist at service/domain query level.

--------------------------------
2.2 Credential lifecycle
--------------------------------

Audit:

- connect
- validate
- sync
- disconnect
- revoke
- reconnect

Important:

Disconnecting an account must not accidentally leave stale authenticated credentials available.

Clarify and implement correct semantics for:

    Disconnect account
    Revoke stored credentials
    Reconnect account

Credentials must remain encrypted and must never be returned to frontend APIs.

Add tests for lifecycle behavior.

--------------------------------
2.3 Windows user-data storage
--------------------------------

Current runtime paths were historically based on project/process working directory.

For a real installed Windows application, design a proper application-data location:

    %LOCALAPPDATA%\CodeMemory\

Potential contents:

    codememory.duckdb
    settings
    accounts/credentials
    knowledge
    logs
    other runtime files

IMPORTANT:
This is a migration, not a simple path replacement.

Before implementing:

- inspect current config
- inspect sidecar process working directory
- inspect storage initialization
- inspect credential storage
- inspect knowledge/export paths
- inspect tests
- inspect PyInstaller behavior

Design migration/compatibility carefully.

Do NOT delete existing user data.

If migration is needed, preserve existing data.

Document the migration.

--------------------------------
2.4 Sidecar lifecycle / console UX
--------------------------------

The end user should NOT see a backend console window when launching CodeMemory.

Desired:

    Launch CodeMemory
       |
       +-- sidecar starts invisibly
       |
       +-- frontend loads
       |
       +-- app works
       |
       +-- close app
              |
              +-- sidecar terminates

Verify:

- startup
- health readiness
- crash handling
- close
- restart
- stale process handling
- port handling

Do not introduce dynamic ports unless necessary.

Do not break existing sidecar verification.

--------------------------------
2.5 Desktop persistence
--------------------------------

Test:

    install
    launch
    connect
    sync
    close
    reopen

Data should remain.

Test with:
- public LeetCode account
- authenticated account
- existing data
- empty data

CHECKPOINT:
Run relevant backend tests, frontend checks, cargo check, and production Tauri build where appropriate.

Report exact results.

==================================================
9. PHASE 3 — PRODUCT UX / ONBOARDING
==================================================

Goal:
Turn the desktop app into a proper application instead of a miniature marketing site.

--------------------------------
3.1 Remove/repurpose desktop marketing homepage
--------------------------------

The current desktop homepage should no longer be the main product landing page.

The marketing homepage will move to:

    website/

For the desktop app, replace the homepage behavior with first-launch onboarding.

--------------------------------
3.2 First-launch onboarding
--------------------------------

Implement:

    no account / first launch
        ->
    CodeMemory intro
        ->
    Get Started
        ->
    LeetCode username
        ->
    sync
        ->
    dashboard

Keep it visually consistent with the existing CodeMemory design system.

Use the current:
- typography
- spacing
- colors
- components
- restrained LeetCode orange
- modern minimal visual style

Do NOT introduce:
- gradients everywhere
- excessive cards
- fake AI visuals
- unnecessary animations
- generic SaaS dashboard design

--------------------------------
3.3 Returning users
--------------------------------

If configured:

    launch
      ->
    dashboard

No onboarding every time.

--------------------------------
3.4 Empty/no-account state
--------------------------------

If no account is configured:

Provide a clear path to:

    Connect LeetCode

The UX should distinguish:

- first launch
- no connected account
- connected account
- disconnected account

--------------------------------
3.5 Remove fake/mock UI
--------------------------------

Remove or replace fake production-looking values identified in previous audits:

- hardcoded memory document counts
- fake "last indexed" timestamps
- mock Data & Sync sections
- mock landing-page product data
- hardcoded revision topic filtering where inappropriate

Do not invent replacement data.

If functionality isn't implemented yet, present an honest empty state.

--------------------------------
3.6 Settings quality
--------------------------------

Improve:
- loading states
- error states
- optimistic update rollback
- settings persistence
- account state feedback

Do not swallow meaningful errors.

CHECKPOINT:
Run full relevant tests and production frontend build.

==================================================
10. PHASE 4 — PUBLIC CODEMEMORY WEBSITE
==================================================

Create a separate public website application.

Recommended structure:

    CodeMemory/
      frontend/       <- desktop application
      website/        <- public website
      src/
      backend/
      tests/
      docs/

The public website must be independent of the desktop app runtime.

It must NOT depend on:
- DuckDB
- local FastAPI
- LeetCode credentials
- Tauri APIs

--------------------------------
4.1 Website routes
--------------------------------

At minimum:

    website/
      /
      /download

Potential future routes:

    /docs
    /changelog
    /releases

Do not overbuild future pages now.

--------------------------------
4.2 Website homepage
--------------------------------

Create a polished CodeMemory product landing page.

Purpose:

Someone who has never used CodeMemory should understand:

- what it is
- who it is for
- what it remembers
- how LeetCode connects
- why local-first matters
- what the desktop app provides
- how to download it

Suggested structure:

Hero:

    CodeMemory
    Your coding history, remembered.

    Turn your LeetCode history into a searchable,
    evolving memory of how you solve problems.

    [ Download for Windows ]
    [ Explore CodeMemory ]

Then sections for:

- Submission history
- Solution evolution
- Mistake/pattern memory
- Search
- Revision
- Analytics
- Local-first/privacy

Use actual product screenshots where available.

Do not invent unsupported features.

--------------------------------
4.3 Download page
--------------------------------

Create:

    /download

Example:

    Download CodeMemory

    Windows
    CodeMemory for Windows
    Windows 10/11 • x64

    [ Download for Windows ]

    Version X.Y.Z

Also provide appropriate release information.

The installer link should be configurable rather than hardcoded throughout components.

Design it so later we can support:

    Windows
    macOS
    Linux

without redesigning the page.

--------------------------------
4.4 Website visual system
--------------------------------

The website and desktop app should clearly belong to the same product.

But do not force identical layouts.

Use:
- same brand
- same typography
- same visual language
- same restrained color system

The website can be more marketing-oriented.

The desktop app remains utility-oriented.

--------------------------------
4.5 Deployment
--------------------------------

Do not assume a final hosting provider unless the repository already establishes one.

Prepare the website for static deployment where practical.

Document:
- build command
- output directory
- environment variables
- deployment assumptions

CHECKPOINT:
Verify:
- homepage
- download page
- links
- responsive behavior
- production build

==================================================
11. PHASE 5 — WINDOWS RELEASE / DISTRIBUTION
==================================================

Goal:
Make the entire journey work:

    Website
      ->
    Download
      ->
    Installer
      ->
    Install
      ->
    First launch
      ->
    Onboarding
      ->
    LeetCode
      ->
    Dashboard

--------------------------------
5.1 Versioning
--------------------------------

Establish a clear version source.

Avoid having:
- package version
- Tauri version
- website version
- installer version

randomly disagree.

Use the repository's existing versioning mechanism where possible.

--------------------------------
5.2 Installer
--------------------------------

Verify:

- MSI
- NSIS installer

Ensure both contain:
- static frontend
- FastAPI sidecar
- required resources

Do not ship source code unnecessarily.

--------------------------------
5.3 Fresh installation test
--------------------------------

Test on a clean-ish Windows environment if available.

Flow:

    download installer
    install
    launch
    onboarding
    username
    sync
    dashboard

--------------------------------
5.4 Upgrade test
--------------------------------

Test:

    previous installation
      ->
    newer installer
      ->
    existing data preserved

Especially test:
- DuckDB
- settings
- account connection
- credentials
- knowledge
- app preferences

--------------------------------
5.5 Release artifact hosting
--------------------------------

The website download page should link to the actual release artifact.

Prefer a release system suitable for versioned binaries, such as GitHub Releases, if that matches the project's distribution strategy.

Do not upload huge generated build artifacts into the Git repository itself.

--------------------------------
5.6 Production smoke test
--------------------------------

Final Windows test:

    Fresh install
       |
       v
    Intro
       |
       v
    Username
       |
       v
    Public sync
       |
       v
    Dashboard
       |
       v
    Auth credentials
       |
       v
    Full sync
       |
       v
    Submission detail
       |
       v
    Search
       |
       v
    Revision
       |
       v
    Analytics
       |
       v
    Restart
       |
       v
    Data persists

Also test account switching/isolation.

==================================================
12. PHASE 6 — FINAL CLEANUP / DOCUMENTATION / REGRESSION
==================================================

--------------------------------
6.1 Generated artifacts
--------------------------------

Audit and clean local generated artifacts:

- .next
- out
- Tauri target
- build
- dist
- node_modules where appropriate
- .rust
- other generated files

Do NOT blindly delete things.

Verify .gitignore first.

Do not delete required local runtime data.

--------------------------------
6.2 Documentation
--------------------------------

Update documentation for:

- LeetCode authentication
- current offset-based pagination
- Tauri development
- Tauri production build
- sidecar
- Windows installation
- website
- release process
- runtime data locations
- migration behavior

Remove outdated instructions.

--------------------------------
6.3 Tests
--------------------------------

Run the complete relevant backend suite.

Run:

    npm run typecheck
    npm run build
    cargo check
    npm run tauri build

where applicable.

Do not hide failures.

If unrelated pre-existing tests fail, clearly identify them.

--------------------------------
6.4 Final regression
--------------------------------

Verify:

BACKEND
- API health
- dashboard
- problems
- submissions
- search
- revision
- settings
- LeetCode public
- LeetCode authenticated
- account isolation

FRONTEND
- navigation
- submission detail
- search
- settings
- onboarding
- empty states

WINDOWS
- installer
- launch
- sidecar
- persistence
- restart
- close
- LeetCode
- credentials

WEBSITE
- homepage
- download page
- installer link
- responsive layout

==================================================
13. GIT / CHANGE MANAGEMENT RULES
==================================================

This is important.

DO NOT:
- automatically commit
- automatically push
- rewrite history
- force push
- reset user changes
- delete branches
- merge branches automatically

Before modifying:

    git status
    git branch --show-current

Do not overwrite unrelated teammate changes.

If the working tree is dirty:
- inspect the changes
- distinguish existing teammate work from your work
- preserve unrelated changes

Prefer small commits if/when I explicitly ask for commits.

Suggested phase commit boundaries:

    Phase 1: fix current UI bugs
    Phase 2: desktop hardening
    Phase 3: onboarding/product UX
    Phase 4: public website
    Phase 5: release/distribution
    Phase 6: cleanup/docs

But DO NOT commit unless instructed.

==================================================
14. DESIGN PRINCIPLES
==================================================

CodeMemory should feel:

- modern
- technical
- minimal
- calm
- local-first
- trustworthy
- developer-focused

Use the existing design language.

Avoid:
- AI slop
- excessive gradients
- excessive glassmorphism
- giant rounded cards
- fake metrics
- fake testimonials
- fake user counts
- invented product claims
- unnecessary animations
- generic SaaS templates

The product should feel closer to:
- Raycast
- Linear
- Vercel
- GitHub Desktop
than a generic startup landing page.

==================================================
15. VERY IMPORTANT EXECUTION METHOD
==================================================

Do NOT immediately implement all six phases.

First:

1. Inspect repository.
2. Inspect Git status.
3. Inspect current architecture.
4. Inspect recent Tauri implementation.
5. Inspect current frontend routing.
6. Inspect LeetCode/account implementation.
7. Inspect existing tests.
8. Produce a concise implementation plan mapped to these six phases.

Then implement:

    Phase 1
      ↓
    verify
      ↓
    checkpoint/report
      ↓
    Phase 2
      ↓
    verify
      ↓
    checkpoint/report
      ↓
    ...

Do not skip verification.

If a phase reveals a major architectural conflict:
STOP.
Explain:
- what you found
- why it matters
- affected files
- possible approaches
- safest recommendation

Do not make a large speculative change without approval.

==================================================
16. FINAL SUCCESS CRITERIA
==================================================

The final product should provide this experience:

NEW USER:

    codememory.dev
        ↓
    Download CodeMemory
        ↓
    Windows installer
        ↓
    Install
        ↓
    Launch
        ↓
    "Your coding history, remembered."
        ↓
    Get Started
        ↓
    Enter LeetCode username
        ↓
    Public sync
        ↓
    Dashboard

RETURNING USER:

    Launch CodeMemory
        ↓
    Dashboard

AUTHENTICATED USER:

    Settings
        ↓
    Connect authenticated LeetCode credentials
        ↓
    Full history sync
        ↓
    submissions + code + failed attempts
        ↓
    memory / analytics / revision / search

MULTI-ACCOUNT:

    Account A
        ↓
    only A data

    switch to Account B
        ↓
    only B data

WEBSITE:

    codememory.dev
        ↓
    product information
        ↓
    features/screenshots
        ↓
    Download
        ↓
    Windows installer

The result should be a coherent product rather than a collection of working technical pieces.

Start by auditing the repository and Git state, then report your findings and Phase 1 plan before making changes.r