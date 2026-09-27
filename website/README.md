# CodeMemory website

The public product site: the same homepage the desktop application shipped,
presented as a standalone static build. It has no FastAPI, DuckDB, Tauri,
account, credential or runtime-data dependency — the only data it reads is
`../release.json`, at build time.

## Pages

| Route | Purpose |
| --- | --- |
| `/` | Product homepage — hero, memory trace, solution evolution, analytics, knowledge graph, revision queue, closing call to action |
| `/download` | Windows installers, release status and installation notes |
| `/about` | What CodeMemory is, how it is built, where data lives |
| `/changelog` | Version history for the current release |
| `/privacy` | What the application and this site read and store |
| `/terms` | MIT license and terms of use |
| `/contact` | Where to file bugs, ask about releases, report security issues |
| `404` | Unknown addresses |

Downloads, docs and releases pages exist only when there is real content for
them; there is no placeholder route.

## Commands

From the repository root:

```powershell
npm --prefix website ci
npm --prefix website run typecheck
npm --prefix website run build
npm --prefix website test
npm --prefix website run preview
```

`npm --prefix website run dev` starts the Next.js development server on
`http://127.0.0.1:4173`. `preview` serves the built `out/` directory on the same
port. Output: `website/out`.

## How the homepage relates to the desktop application

The homepage, its sections and its components came from the desktop application's
product homepage (`frontend/app/page.tsx` before the productization pass). The
website keeps those components under `website/components` and the design tokens
in `website/app/globals.css`; only destinations changed, because the public site
has no application routes:

- `Connect LeetCode`, `Open CodeMemory` and `Browse problems` link to `/download`.
- The footer carries the public pages instead of Dashboard/Analytics/Knowledge/Settings.
- Demo rows that opened a problem in the workspace now open `/download`.

Nothing in the website imports the desktop application's API client, settings
store or runtime paths.

## Release configuration

`../release.json` remains the single source of truth. It is read by
`next.config.ts` (in Node) and inlined into the build, so no page reaches outside
`website/` at build time. While `published` is false, the download buttons render
disabled with an explanation and no artifact URL is emitted.

For a self-hosted build with real installers:

```powershell
./scripts/collect-release.ps1
$env:CODEMEMORY_RELEASE_DIR = (Resolve-Path build/release).Path
npm --prefix website run build   # also copies artifacts into out/releases/v<version>/
Remove-Item Env:CODEMEMORY_RELEASE_DIR
```

## Deployment

Deploy the contents of `out/` to a static host at the domain root, so unknown
addresses serve `404.html` and `/download/` resolves to `download/index.html`.
Root-relative asset URLs require a domain-root deployment. No environment
variables are required at runtime. See [release instructions](../docs/windows-release.md).
