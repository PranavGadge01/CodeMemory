# CodeMemory — Frontend Foundation Master Prompt

You are the frontend lead for the CodeMemory project.

## CRITICAL SCOPE RULE

A new dedicated frontend directory has been created at:

    /frontend

From this point forward, ALL frontend work must happen inside `frontend/`.

### HARD BOUNDARY

You MUST NOT modify, delete, rename, move, refactor, or reorganize anything outside `frontend/`.

Treat the entire repository outside `frontend/` as READ-ONLY.

In particular:

- DO NOT modify backend code.
- DO NOT modify Python code.
- DO NOT modify database/storage code.
- DO NOT modify domain models.
- DO NOT modify LeetCode connectors.
- DO NOT modify sync logic.
- DO NOT modify CLI code.
- DO NOT modify existing backend configuration.
- DO NOT modify backend tests.
- DO NOT modify root project architecture.
- DO NOT "clean up" unrelated files.
- DO NOT integrate with the backend yet.
- DO NOT create API routes that depend on the backend.
- DO NOT add authentication logic.
- DO NOT connect to DuckDB/Postgres/any database.
- DO NOT implement real LeetCode synchronization.
- DO NOT change existing backend dependencies.

If something outside `frontend/` appears to need modification, STOP and report it instead of changing it.

The only exception is reading existing repository files to understand the project.

Your job in this phase is to build a polished, production-quality FRONTEND FOUNDATION inside `frontend/`.

---

# 1. FIRST: STUDY THE PROJECT

Before writing code:

1. Inspect the repository structure.
2. Inspect the existing `frontend/` directory.
3. Inspect the existing backend/project structure ONLY to understand the product and existing concepts.
4. Read:

    frontend/DESIGN.md

This `DESIGN.md` is the primary visual/design specification for the frontend.

Treat it as the source of truth for the CodeMemory visual language.

Do not replace it with your own generic design system.

You should understand the existing CodeMemory product concept, but frontend implementation must remain isolated inside `frontend/`.

Spend roughly 10–15 minutes understanding the repository and design direction before implementing.

Then begin implementation.

---

# 2. PRODUCT CONTEXT

CodeMemory is a personal coding-intelligence and learning-memory product.

It helps developers understand and remember their coding journey.

The product revolves around things such as:

- coding problem history
- LeetCode problems
- submissions
- solution evolution
- coding patterns
- analytics
- knowledge
- revision
- learning progress
- personal coding memory

The frontend should feel like a serious developer product rather than a generic SaaS dashboard.

It should communicate:

"Your coding history, remembered."

But do not make the entire interface feel like a marketing website.

The product should feel useful, technical, intelligent, calm, and polished.

---

# 3. DESIGN DIRECTION

Read `frontend/DESIGN.md` completely before implementing.

The overall visual direction combines:

### Vercel / Geist

Use this as the structural and typographic foundation:

- Geist Sans
- Geist Mono
- precise typography
- restrained UI
- strong hierarchy
- hairline borders
- clean developer-tool aesthetic
- excellent spacing
- minimal visual noise

### Raycast

Use this primarily for interaction quality:

- premium dark interface
- compact but spacious controls
- strong surface hierarchy
- subtle borders
- excellent hover/focus states
- tactile interactions
- polished transitions
- product-first visual storytelling

### LeetCode

Use LeetCode as contextual inspiration:

- coding-oriented visual language
- problem difficulty concepts
- coding statistics
- recognizable orange accent
- developer familiarity

BUT:

DO NOT CLONE LEETCODE.

CodeMemory must have its own identity.

### CodeMemory

Create a distinct identity around:

- memory
- coding history
- solution evolution
- patterns
- learning
- revision
- knowledge connections

The interface should feel like a developer's personal coding memory system.

---

# 4. CORE VISUAL LANGUAGE

Follow `frontend/DESIGN.md`.

Important principles:

- dark-first
- minimal
- premium
- technical
- calm
- highly readable
- restrained use of color
- strong whitespace
- subtle borders
- minimal shadows
- no visual clutter

Primary canvas should be near-black.

Use the CodeMemory orange accent sparingly.

Orange should communicate:

- brand
- important actions
- selected states
- meaningful highlights

Do NOT make the entire UI orange.

Use semantic colors only where appropriate.

---

# 5. TYPOGRAPHY

Use:

- Geist Sans for normal UI
- Geist Mono for code, metrics, technical identifiers, timestamps, IDs, etc.

Typography should feel intentional.

Avoid:

- huge generic SaaS headings everywhere
- excessive font weights
- overly rounded typography
- unnecessary uppercase labels

Use tight display typography where appropriate.

---

# 6. ICONS

Use Lucide icons or the existing icon system if already configured.

Rules:

- icons should communicate meaning
- consistent stroke weight
- compact sizing
- no random decorative icons
- no emoji
- no sparkle icons
- no "AI slop" visual language

Do not add icons just to fill empty space.

---

# 7. ANIMATION / MOTION

The interface should feel responsive, not animated for the sake of being animated.

Use:

- subtle hover transitions
- button press feedback
- small scale-down on press
- smooth state transitions
- tasteful page/section reveals
- subtle chart transitions
- restrained layout transitions

We specifically want polished interaction details.

For example, buttons can have a subtle tactile response when clicked.

For certain state-changing buttons, use a morphing transition:

old label visually exits/wipes → icon moves/transitions → new state appears.

Keep it fast and subtle.

Avoid:

- bouncing UI
- excessive spring animations
- glowing UI
- infinite animations
- floating objects everywhere
- excessive parallax
- animation overload
- distracting backgrounds

Use CSS transitions for simple interactions.

Use GSAP only when it materially improves the experience.

Relevant GSAP skills may be used where appropriate.

---

# 8. SKILLS

Use the relevant installed skills when implementing.

Prioritize them in this order:

1. `frontend-design`
2. `shadcn`
3. GSAP skills when animation is actually needed
4. `ui-ux-pro-max`
5. `minimalist-ui`
6. Other relevant skills only when useful

Relevant GSAP skills include:

- `gsap-core`
- `gsap-react`
- `gsap-timeline`
- `gsap-scrolltrigger`
- `gsap-performance`
- `gsap-utils`

Do not force a skill into the implementation.

Use the skills as design/implementation guidance, not as an excuse to over-engineer.

The CodeMemory `frontend/DESIGN.md` takes precedence over generic skill recommendations.

---

# 9. TECHNOLOGY

First inspect what exists inside `frontend/`.

If the frontend is already initialized, use the existing stack rather than replacing it.

Prefer:

- Next.js
- React
- TypeScript
- Tailwind CSS
- shadcn/ui
- Geist
- Lucide

Use the App Router if Next.js is already configured that way.

Do not introduce unnecessary dependencies.

Do not rewrite the frontend stack just because another technology is available.

Keep the frontend maintainable and production-oriented.

---

# 10. IMPORTANT: FRONTEND ONLY / MOCK DATA

This phase is FRONTEND ONLY.

There is NO backend integration yet.

Build the UI using realistic mock data.

Create a clean mock-data layer inside `frontend/`, for example:

    frontend/lib/mock/

or another sensible equivalent.

Mock data should resemble realistic CodeMemory data:

- problems
- submissions
- languages
- difficulty
- timestamps
- streaks
- patterns
- solution versions
- analytics
- revision items
- knowledge nodes

Do NOT hardcode huge datasets directly into page components.

Create reusable mock data structures.

The architecture should make it easy to replace mock data with real API calls later.

For example:

    UI component
        ↓
    frontend data/service abstraction
        ↓
    mock data for now

Later:

    UI component
        ↓
    frontend data/service abstraction
        ↓
    backend API

But DO NOT implement the backend integration now.

---

# 11. ROUTES / PAGES

Create the initial frontend application with these conceptual pages:

## Public

### `/`

This is the MOST IMPORTANT page.

It represents the CodeMemory brand.

It should be attractive, memorable, and immediately communicate what CodeMemory is.

This is NOT a generic SaaS landing page.

It should feel like entering the actual product.

---

## Application

### `/dashboard`

Personal coding overview.

Show things such as:

- recent activity
- solved problems
- streak
- difficulty distribution
- language distribution
- recent submissions
- coding activity
- learning/revision signals

The dashboard should feel useful rather than decorative.

---

### `/problems`

Problem history and exploration.

Include:

- problem list
- search
- filters
- difficulty
- status
- language
- tags/patterns
- solved/attempted states
- useful metadata

Use realistic mock data.

---

### `/submissions`

Submission history.

Show:

- problem
- language
- status
- timestamp
- runtime
- memory
- submission identifier
- solution version/context where appropriate

Use a clean developer-oriented table/list.

---

### `/analytics`

A deeper coding analytics page.

Potential sections:

- activity over time
- solved problems
- difficulty distribution
- language usage
- acceptance trends
- problem patterns
- consistency
- solving behavior
- solution evolution metrics

Charts must communicate information.

Do not create decorative charts without meaning.

---

### `/knowledge`

Knowledge/memory view.

This should visually represent the idea of CodeMemory's knowledge layer.

Potential concepts:

- coding patterns
- concepts
- problem relationships
- language knowledge
- topic clusters
- knowledge graph
- connections between problems and patterns

This page can use an elegant graph-like visualization or structured knowledge interface.

Do not make it visually chaotic.

---

### `/revision`

Revision / learning queue.

Show:

- problems to revisit
- concepts to revise
- weak patterns
- recently forgotten topics
- revision priority
- progress

The page should feel like an intelligent study workspace.

---

### `/settings`

Frontend settings UI.

Include appropriate sections such as:

- appearance
- account
- preferences
- sync-related UI placeholders
- data/preferences
- about

IMPORTANT:

These are visual placeholders only for now.

Do not implement actual authentication, account APIs, sync, or destructive backend operations.

---

### `/auth/sign-in`

Create a polished sign-in UI shell.

It can be visually complete but MUST NOT implement real authentication yet.

Use mock interaction/state if necessary.

---

# 12. HOME PAGE — BRAND IDENTITY

The home page is the most important frontend deliverable.

It should immediately feel like CodeMemory.

Core idea:

    "Your coding history, remembered."

The home page should combine brand storytelling with real product UI.

Avoid the standard:

    Navbar
    giant gradient heading
    three feature cards
    testimonials
    pricing
    generic CTA

That would feel like AI-generated SaaS marketing.

Instead, make the product itself the hero.

---

## Suggested home structure

### Navigation

Minimal.

Logo / CodeMemory wordmark.

Links can include:

- Product
- How it works
- Features

And a clear action such as:

- Open CodeMemory
- Get Started

Keep it understated.

---

### Hero

The hero should communicate the product immediately.

Possible direction:

"Your coding history, remembered."

Supporting copy explaining that CodeMemory turns coding history into a searchable, evolving memory of how you solve problems.

Then show a beautiful product visualization.

The product UI should be the visual centerpiece.

For example:

- coding activity timeline
- problem history
- solution evolution
- memory/pattern visualization
- analytics snapshot

Make this feel like an actual product rather than a fake marketing screenshot.

---

### Memory / History section

Show how CodeMemory captures coding history.

Use:

- activity timeline
- problems
- attempts
- submissions
- languages
- timestamps

Create a visual "memory trace" motif.

This should become part of CodeMemory's identity.

---

### Solution Evolution

Show how a solution changes over time.

For example:

    Attempt 1
        ↓
    Attempt 2
        ↓
    Optimized solution
        ↓
    Final understanding

Use a polished code/diff/evolution visualization.

This is one of the strongest product concepts.

---

### Analytics

Show meaningful analytics.

Not generic dashboard cards.

Examples:

- solving consistency
- difficulty progression
- language usage
- topic distribution
- coding activity

The charts should look like actual product analytics.

---

### Knowledge

Introduce the idea that CodeMemory connects:

    Problems
       ↕
    Patterns
       ↕
    Concepts
       ↕
    Solutions

Visualize this elegantly.

---

### Revision

Show that CodeMemory does more than store history.

It helps users revisit things they are likely to forget.

Display a realistic revision queue.

---

### Final CTA

End with a strong but understated CTA.

Avoid aggressive marketing language.

The final section should reinforce:

"Your code has a history. Make it useful."

---

# 13. APPLICATION SHELL

Create a consistent application shell for authenticated/product pages.

Preferred structure:

    Sidebar
    ─────────────
    Overview
    Problems
    Submissions
    Analytics
    Knowledge
    Revision

    Settings
    ─────────────

Main content area.

The sidebar should feel closer to a premium developer tool than a traditional enterprise dashboard.

Include:

- active state
- subtle hover
- compact navigation
- keyboard-friendly interactions
- optional collapse behavior if appropriate

Do not make the sidebar oversized.

---

# 14. DASHBOARD DESIGN

The dashboard should NOT just be:

    4 statistic cards
    giant chart
    recent table

Instead create a useful information hierarchy.

Possible layout:

- greeting / context
- activity summary
- coding activity visualization
- recent problems
- solution evolution
- patterns
- revision signals

Cards should be used only where they improve grouping.

Avoid excessive card nesting.

---

# 15. PROBLEMS PAGE

Create a polished problem browser.

Features can include:

- search
- filtering
- sorting
- difficulty
- solved state
- tags
- language
- date

Use realistic data.

Make the table/list highly readable.

Consider expandable rows or a detail panel if it improves UX.

---

# 16. SUBMISSIONS PAGE

Make this feel like a developer tool.

Potential layout:

- submission table
- status
- runtime
- memory
- language
- timestamp
- problem
- solution version

Use monospace typography selectively.

---

# 17. ANALYTICS PAGE

Charts should follow the visual system.

Prefer:

- subtle gridlines
- restrained colors
- meaningful accent use
- clear labels
- readable tooltips
- strong hierarchy

Do not use rainbow charts.

Do not use charts simply because empty space exists.

---

# 18. KNOWLEDGE PAGE

This is an opportunity for CodeMemory's unique identity.

Explore a visual system around:

    Problem → Pattern → Concept → Solution

Possible UI:

- graph
- connected nodes
- topic clusters
- knowledge cards
- relationship panel

Keep it calm and readable.

Do not create a noisy "AI neural network" aesthetic.

---

# 19. REVISION PAGE

The revision page should feel focused.

Think:

"These are the things your coding memory says you should revisit."

Use:

- priority
- topic
- problem
- last solved
- confidence
- revision state

Make the page feel like a learning workspace rather than another analytics dashboard.

---

# 20. SETTINGS

Settings should follow the same product language.

Use grouped sections rather than huge cards.

Examples:

Appearance
Preferences
Account
Data
Sync
About

Backend functionality should NOT be implemented.

If a setting requires backend functionality, create the UI state only.

---

# 21. COMPONENT ARCHITECTURE

Build reusable components.

Do not put everything into page files.

Create sensible areas such as:

    frontend/
      app/
      components/
      components/ui/
      lib/
      lib/mock/
      public/
      styles/

Adapt this to the existing frontend structure.

Potential reusable components:

- AppShell
- Sidebar
- TopBar
- PageHeader
- Stat
- DataTable
- ProblemRow
- SubmissionRow
- ActivityChart
- DifficultyChart
- Timeline
- SolutionEvolution
- KnowledgeGraph
- RevisionItem
- EmptyState
- StatusBadge
- DifficultyBadge
- SearchInput
- FilterBar

Only create components that are actually useful.

Do not abstract prematurely.

---

# 22. RESPONSIVENESS

The frontend must work across:

- desktop
- laptop
- tablet
- mobile

Desktop is the primary experience.

Do not simply shrink the desktop layout.

Adapt:

- navigation
- tables
- charts
- spacing
- typography
- content density

For mobile, sidebar/navigation should transform appropriately.

---

# 23. ACCESSIBILITY

Use:

- semantic HTML
- keyboard navigation
- visible focus states
- accessible buttons
- accessible labels
- sufficient contrast
- reduced-motion consideration

Do not rely on color alone to communicate status.

---

# 24. PERFORMANCE

Keep the frontend lightweight.

Avoid unnecessary:

- dependencies
- huge animation libraries where CSS is enough
- giant client components
- unnecessary state
- repeated data transformations

Use client components only where interaction actually requires them.

Keep static/content-oriented parts server-renderable where appropriate.

---

# 25. ANTI-AI-SLOP RULES

This is extremely important.

DO NOT produce:

- purple/blue gradient everywhere
- glowing cards
- glassmorphism everywhere
- excessive rounded rectangles
- giant floating blobs
- random decorative sparkles
- "AI" labels everywhere
- generic SaaS illustrations
- fake testimonials
- fake logos
- meaningless metrics
- excessive shadows
- excessive animations
- giant gradient text
- dashboard-card-grid-only layouts

Do not make it look like a template.

The frontend should look deliberately designed.

If a design element does not improve hierarchy, usability, identity, or storytelling, remove it.

---

# 26. BRAND IDENTITY

CodeMemory needs its own visual signature.

Develop the following carefully:

- wordmark treatment
- CodeMemory orange accent
- memory trace/timeline visual language
- solution evolution visualization
- coding-history motifs
- subtle monospace details

These should recur across the product without becoming repetitive.

The goal is:

Vercel's precision
+
Raycast's interaction quality
+
LeetCode's coding familiarity
+
CodeMemory's memory/history identity

NOT a clone of any of them.

---

# 27. IMPLEMENTATION ORDER

Do NOT try to build everything in one giant implementation pass.

Work in checkpoints.

## CHECKPOINT 1 — Foundation

First:

- inspect existing frontend
- read DESIGN.md
- establish typography
- colors
- spacing
- base components
- shadcn configuration if needed
- global styles
- layout foundation
- mock data architecture

Then verify the app runs.

---

## CHECKPOINT 2 — Home / Brand

Build `/`.

This gets the highest design attention.

Make the home page feel production-quality.

Do not rush this page.

---

## CHECKPOINT 3 — Application Shell

Build:

- sidebar
- navigation
- responsive shell
- page header
- shared layout

Then connect the shell to all app routes.

---

## CHECKPOINT 4 — Product Pages

Build:

- dashboard
- problems
- submissions
- analytics
- knowledge
- revision
- settings
- sign-in

Use mock data.

---

## CHECKPOINT 5 — Motion + Polish

Review all pages.

Add only useful motion.

Improve:

- spacing
- typography
- hover states
- active states
- loading states
- empty states
- responsive behavior
- button feedback
- transitions

---

## CHECKPOINT 6 — Validation

Run:

- lint
- typecheck
- build
- tests if frontend tests exist

Fix frontend issues.

Do NOT modify backend code to make frontend validation pass.

If backend-related issues prevent a check, report them instead.

---

# 28. DO NOT STOP AT A WIREFRAME

The result should be a real working frontend.

Not:

- placeholder boxes everywhere
- TODO comments
- empty pages
- giant skeleton loaders
- lorem ipsum
- generic dashboard templates

Use realistic mock content.

Every major route should look intentionally designed.

---

# 29. QUALITY BAR

Before finishing, inspect the frontend as if you were reviewing a premium developer product.

Ask:

- Does this immediately feel like CodeMemory?
- Is the home page memorable?
- Does the product UI itself communicate the product?
- Is the typography excellent?
- Is spacing consistent?
- Are borders subtle?
- Is orange restrained?
- Do interactions feel tactile?
- Does anything feel like generic AI-generated SaaS?
- Are there unnecessary cards?
- Are there unnecessary animations?
- Does the knowledge view feel unique?
- Does solution evolution feel like a CodeMemory concept?
- Does the app shell feel like a serious developer tool?
- Does mobile remain usable?

Fix issues you find.

---

# 30. FINAL HARD CONSTRAINT

Again:

ONLY WORK INSIDE:

    /frontend

Everything outside `/frontend` is READ-ONLY.

You may inspect the rest of the repository for context.

You may NOT modify anything outside `/frontend`.

Do not touch backend code even if you think a backend change would make the frontend easier.

Backend integration comes in a future phase.

For this phase:

    FRONTEND = REAL
    DATA = MOCK
    BACKEND = UNTOUCHED

---

# 31. FINAL REPORT

At the end, report:

1. What was built
2. Routes created
3. Major reusable components
4. Mock-data architecture
5. Skills used
6. Major design decisions
7. Animation/motion implemented
8. Responsive behavior
9. Validation commands run
10. Validation results
11. Any remaining frontend-only issues

Also explicitly confirm:

"Backend files were not modified."

Do not provide a huge essay.

Keep the final report concise and technical.