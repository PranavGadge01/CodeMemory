---
version: 1.0
name: CodeMemory Design System
status: active
---

# CodeMemory Design System

## 1. Product Identity

CodeMemory is a personal coding intelligence and learning-memory system.

It sits between:

- a developer workspace
- a coding history archive
- a learning analytics tool
- a personal knowledge graph
- a LeetCode companion

The product should feel like a tool a serious developer keeps open every day.

### Design personality

CodeMemory is:

- technical
- intelligent
- precise
- minimal
- dark
- calm
- highly usable
- slightly playful through interaction
- information-dense without feeling crowded

CodeMemory is NOT:

- a generic SaaS dashboard
- an AI chatbot interface
- a marketing-heavy startup template
- a glassmorphism dashboard
- a neon cyberpunk interface
- an "AI aesthetic" website
- an icon/emoji showcase

The visual language should communicate:

> "This is my coding memory."

Not:

> "This is another AI productivity app."

---

# 2. Design Inspiration

CodeMemory takes inspiration from three ecosystems but must remain visually distinct.

## Vercel / Geist

Borrow:

- typography discipline
- Geist Sans
- Geist Mono
- precise spacing
- strong hierarchy
- minimal surfaces
- thin borders
- developer-oriented visual language
- restrained component geometry

Do NOT copy:

- Vercel's exact layouts
- Vercel branding
- Vercel gradients
- Vercel's white-first aesthetic

The uploaded Vercel analysis emphasizes Geist typography, tight display tracking, hairline borders and restrained component geometry. CodeMemory should preserve those principles while moving them into a dark environment.

## Raycast

Borrow:

- dark developer-tool canvas
- near-black surface hierarchy
- command-palette visual language
- compact controls
- hairline borders
- information density
- subtle interaction feedback
- "product UI as identity"

Do NOT copy:

- Raycast branding
- Raycast's red stripe motif
- Raycast's exact command palette
- Raycast's extension-store visual language

Raycast's strongest applicable principle is:

> The interface itself should be the visual identity.

## LeetCode

Borrow conceptually:

- coding familiarity
- problem difficulty semantics
- developer-oriented information density
- coding/problem language
- recognizable orange as a restrained brand accent
- familiar concepts such as Easy / Medium / Hard
- submission/problem/history relationships

Do NOT copy:

- LeetCode layouts
- LeetCode navigation
- LeetCode cards
- LeetCode exact colors
- LeetCode visual hierarchy

LeetCode is an inspiration for familiarity, not a template.

---

# 3. Core Visual Concept

### "Dark Coding Memory"

The UI should feel like a dark developer workspace containing a personal map of coding knowledge.

The dominant visual language:

    near-black canvas
          ↓
    subtle surface ladder
          ↓
    thin borders
          ↓
    precise typography
          ↓
    orange semantic accents
          ↓
    data + code + relationships

Avoid visual noise.

If removing an element makes the interface clearer, remove it.

---

# 4. Color System

## Base

canvas:
  #07080A

surface:
  #0C0D0F

surface-elevated:
  #101214

surface-card:
  #141618

surface-hover:
  #181A1D

surface-active:
  #1C1F22

## Borders

border:
  rgba(255,255,255,0.09)

border-soft:
  rgba(255,255,255,0.055)

border-strong:
  rgba(255,255,255,0.15)

Do not use heavy borders.

## Text

text-primary:
  #F5F5F5

text-secondary:
  #B5B7BA

text-muted:
  #85888C

text-faint:
  #5F6266

text-disabled:
  #45484C

Never use pure white for large amounts of body text.

## CodeMemory Accent

The primary brand accent is a restrained LeetCode-inspired orange.

accent:
  #FFA116

accent-hover:
  #FFB13B

accent-pressed:
  #E8910F

accent-soft:
  rgba(255,161,22,0.12)

accent-border:
  rgba(255,161,22,0.30)

Orange is an identity accent, NOT the color of every button.

Use it for:

- important active states
- selected navigation
- key product moments
- progress indicators
- coding-related highlights
- primary interactive emphasis where appropriate

Do not turn the entire UI orange.

---

# 5. Semantic Colors

success:
  #3ECF8E

success-soft:
  rgba(62,207,142,0.12)

warning:
  #F5B942

warning-soft:
  rgba(245,185,66,0.12)

error:
  #FF5C5C

error-soft:
  rgba(255,92,92,0.12)

info:
  #57A8FF

info-soft:
  rgba(87,168,255,0.12)

Semantic colors communicate state.

They are NOT decorative colors.

---

# 6. Difficulty Colors

Difficulty should be immediately recognizable but restrained.

easy:
  #3ECF8E

medium:
  #FFA116

hard:
  #FF5C5C

Use soft backgrounds when possible.

Example:

Easy
  green text
  subtle green background

Medium
  orange text
  subtle orange background

Hard
  red text
  subtle red background

Do not create giant colored difficulty cards.

---

# 7. Typography

## Primary

Geist Sans

Use Geist for:

- navigation
- headings
- body
- buttons
- labels
- dashboard
- analytics

## Technical

Geist Mono

Use Geist Mono for:

- code
- runtime
- memory
- Big-O
- submission IDs
- timestamps
- technical metadata
- terminal-like elements
- small technical eyebrows

Do not use monospace everywhere.

---

## Type Scale

display-xl:
  font: Geist Sans
  size: 64px
  weight: 600
  line-height: 1.05
  letter-spacing: -2.5px

display-lg:
  font: Geist Sans
  size: 48px
  weight: 600
  line-height: 1.1
  letter-spacing: -1.8px

heading-xl:
  font: Geist Sans
  size: 32px
  weight: 600
  line-height: 1.2
  letter-spacing: -1px

heading-lg:
  font: Geist Sans
  size: 24px
  weight: 600
  line-height: 1.3
  letter-spacing: -0.5px

heading-md:
  font: Geist Sans
  size: 20px
  weight: 600
  line-height: 1.35

heading-sm:
  font: Geist Sans
  size: 16px
  weight: 600
  line-height: 1.4

body-lg:
  font: Geist Sans
  size: 16px
  weight: 400
  line-height: 1.6

body-md:
  font: Geist Sans
  size: 14px
  weight: 400
  line-height: 1.5

body-sm:
  font: Geist Sans
  size: 13px
  weight: 400
  line-height: 1.5

caption:
  font: Geist Sans
  size: 12px
  weight: 400
  line-height: 1.4

technical:
  font: Geist Mono
  size: 13px
  weight: 400
  line-height: 1.5

technical-small:
  font: Geist Mono
  size: 11px
  weight: 500
  line-height: 1.4
  letter-spacing: 0.02em

---

# 8. Spacing

Use a 4px base grid.

2px
4px
8px
12px
16px
20px
24px
32px
40px
48px
64px
80px
96px
128px

Default component spacing:

small:
  8px

normal:
  12–16px

card:
  20–24px

large section:
  64–96px

Do not make every section enormous.

CodeMemory is a tool, not a landing-page-only experience.

---

# 9. Layout

Desktop application:

max-width:
  1440px

Marketing/home content:

max-width:
  1200–1280px

Dashboard:

Use a persistent sidebar + main workspace.

Example:

┌──────────────┬─────────────────────────────────────┐
│              │                                     │
│  CodeMemory  │           Main Workspace            │
│              │                                     │
│  Dashboard   │                                     │
│  Problems    │                                     │
│  Submissions │                                     │
│  Analytics   │                                     │
│  Knowledge   │                                     │
│  Revision    │                                     │
│              │                                     │
│  Settings    │                                     │
│              │                                     │
└──────────────┴─────────────────────────────────────┘

The sidebar should feel like a developer application sidebar, not a generic SaaS admin template.

---

# 10. Border Radius

Use restrained rounding.

none:
  0px

sm:
  6px

md:
  8px

lg:
  12px

xl:
  16px

pill:
  9999px

Most UI:

buttons:
  8px

inputs:
  8px

cards:
  10–12px

large visual panels:
  12–16px

Do not use 20–32px rounded cards throughout the application.

Avoid "everything is a pill."

---

# 11. Elevation

Prefer surface changes and borders over shadows.

Default:

background + border

Elevated:

one surface step lighter

Floating:

subtle shadow + border

Never use:

- huge shadows
- glowing shadows
- neon outlines
- excessive blur

Depth should be quiet.

---

# 12. Cards

Cards should be used to group meaningful information.

Do not turn every piece of content into a card.

Good:

┌─────────────────────────────────┐
│ Solving Activity                │
│                                 │
│ graph / data visualization      │
│                                 │
└─────────────────────────────────┘

Bad:

┌─────────┐ ┌─────────┐ ┌─────────┐
│ icon    │ │ icon    │ │ icon    │
│ number  │ │ number  │ │ number  │
└─────────┘ └─────────┘ └─────────┘

Avoid excessive dashboard-card grids.

Prefer meaningful compositions.

---

# 13. Navigation

## Public Navigation

Logo:

CodeMemory

Navigation can include:

Product
How it works
Insights
About

Right:

Sign in
Open CodeMemory

Keep it compact.

## Application Navigation

Primary:

Overview
Problems
Submissions
Analytics
Knowledge
Revision

Secondary:

Search
Settings

The navigation should be recognizable without requiring icons everywhere.

Icons are supporting elements, not labels.

---

# 14. Iconography

Use one coherent icon library.

Prefer Lucide icons when an icon is genuinely useful.

Rules:

- icons should communicate function
- 16–18px typical size
- 1.5–2px stroke
- consistent visual weight
- never use icons simply to fill empty space

Do NOT:

- place an icon beside every text label
- use emojis as UI icons
- use random icon styles
- use decorative sparkles
- use AI sparkle icons

No:

✨
🚀
🔥
🧠

unless the user explicitly creates such content.

---

# 15. Home Page Philosophy

The home page is the brand identity of CodeMemory.

It should be the most visually distinctive page.

The home page should answer immediately:

1. What is CodeMemory?
2. Why does it exist?
3. What does it remember?
4. What does it help me understand?

The hero should feel like a **product interface**, not a generic SaaS hero.

---

# 16. Home Hero

Hero concept:

"Your coding history, remembered."

Possible supporting message:

"CodeMemory turns your coding history into searchable knowledge, measurable progress, and a memory of how you solve problems."

The hero should visually show the product.

Possible hero composition:

Left:
  strong headline
  concise description
  primary CTA
  secondary CTA

Right / below:
  large CodeMemory product visualization

The product visualization could combine:

- problem history
- submission timeline
- difficulty indicators
- analytics
- knowledge relationships
- code snippets
- revision signals

The interface itself is the hero decoration.

Avoid stock photography.

Avoid generic 3D illustrations.

Avoid giant abstract AI blobs.

---

# 17. CodeMemory Visual Motif

A recurring visual motif should be:

## "Memory traces"

Use subtle lines, nodes, timelines and connections to represent coding memory.

Example:

Problem
   │
   ├── Submission
   │
   ├── Pattern
   │
   ├── Concept
   │
   └── Revision

These relationships can appear visually in:

- hero
- knowledge graph
- analytics
- solution evolution
- revision interface

This becomes a CodeMemory-specific visual identity.

---

# 18. Data Visualization

Analytics should feel like a developer tool.

Prefer:

- line charts
- compact bar charts
- heatmaps
- timelines
- distribution charts
- knowledge graphs

Avoid:

- giant donut charts for trivial metrics
- 3D charts
- excessive gradients
- rainbow charts
- chart decorations

Use orange primarily for the selected/important series.

Use semantic colors only when they carry meaning.

---

# 19. Motion System

Motion is functional.

The interface should feel responsive, not animated.

## Micro interaction

80–150ms

Use for:

- button press
- hover
- toggles
- icon transitions
- selection

Example:

scale:
  1 → 0.97 → 1

## UI transition

180–300ms

Use for:

- sidebar
- dropdown
- tabs
- panels
- modal
- expanding content

## Meaningful transition

300–500ms

Use for:

- knowledge graph
- solution evolution
- analytics transitions
- timeline movement

Never make interactions slow.

---

# 20. Button Motion

Buttons should feel physical.

Example:

Normal:

[ View solution → ]

Click:

[ View solution → ]
       ↓
[View solution →]  slightly compressed
       ↓
[     →          ]
       ↓
[     ✓          ]

Morphing is encouraged for meaningful state changes.

However:

- animation must never delay the action
- avoid bounce
- avoid excessive spring
- avoid glow
- avoid infinite motion

---

# 21. GSAP

Use GSAP when it provides meaningful interaction or sequencing.

Relevant skills:

- gsap-core
- gsap-react
- gsap-timeline
- gsap-scrolltrigger
- gsap-performance
- gsap-utils

Do NOT use GSAP for every hover or simple CSS transition.

Prefer CSS for trivial transitions.

Use GSAP for:

- coordinated sequences
- morphing controls
- timeline interactions
- knowledge graph movement
- meaningful page choreography
- complex scroll interactions

Always respect:

prefers-reduced-motion

---

# 22. Accessibility

All interactions must remain accessible.

Requirements:

- keyboard navigation
- visible focus states
- semantic HTML
- adequate contrast
- 44px recommended touch target for important controls
- reduced-motion support
- meaningful aria labels
- no information conveyed only through color

Animation must never be necessary to understand an interaction.

---

# 23. Responsive Design

Desktop:

sidebar + workspace

Tablet:

condensed sidebar / navigation

Mobile:

bottom navigation or compact navigation where appropriate

Never simply shrink desktop UI.

Charts should reflow.

Knowledge graph should remain usable.

Code should horizontally scroll rather than become unreadably small.

Tables should transform into useful mobile layouts.

---

# 24. Anti-AI-Slop Rules

Absolutely avoid:

- purple-blue gradients everywhere
- excessive glassmorphism
- glowing borders
- floating blobs
- AI sparkle icons
- meaningless 3D objects
- giant rounded cards
- excessive pills
- excessive emojis
- random illustrations
- decorative particle systems
- huge shadows
- excessive blur
- "AI" badges everywhere
- generic dashboard templates
- excessive icon usage
- unnecessary animated backgrounds

If a visual element does not improve:

clarity
hierarchy
identity
feedback
or understanding

remove it.

---

# 25. Component Philosophy

Use shadcn/ui as the implementation foundation where appropriate.

Relevant skill:

shadcn

Customize components to match CodeMemory.

Do not let default shadcn styling define the product identity.

Components should inherit CodeMemory:

- colors
- typography
- spacing
- radius
- borders
- interaction
- motion

---

# 26. Design Skill Priority

When multiple skills are available:

1. CodeMemory Design System
2. frontend-design
3. shadcn
4. relevant GSAP skills
5. UI UX Pro Max
6. minimalist-ui

Generic skills are references and implementation aids.

CodeMemory's identity always wins.

---

# 27. Design Quality Test

Before considering a page complete, ask:

### Identity
Does this look like CodeMemory?

### Restraint
Can anything unnecessary be removed?

### Hierarchy
Can the user understand the page in 2–3 seconds?

### Interaction
Does the interface provide satisfying but subtle feedback?

### Density
Is information dense enough for a developer without feeling crowded?

### Consistency
Does it follow the CodeMemory token system?

### Anti-slop
Does anything look like a generic AI-generated SaaS website?

If yes, redesign it.

---

# 28. Final Principle

CodeMemory should feel:

> Quiet when idle.
> Precise when used.
> Alive when interacted with.
> Intelligent without advertising that it is AI.
> Familiar to developers without looking like a LeetCode clone.

The design should make the user's coding history feel like something valuable that has been preserved.