# CodeMemory website

Static product site with `/`, `/download/` and a 404 page. It uses Node only at
build time and local Geist font assets. It has no FastAPI, DuckDB, Tauri, account,
credential or runtime JavaScript dependency.

From the repository root:

```powershell
npm --prefix website ci
npm --prefix website run typecheck
npm --prefix website run build
npm --prefix website test
npm --prefix website run preview
```

Open `http://127.0.0.1:4173`. `npm --prefix website run dev` builds and serves;
re-run build after edits (there is no hot-reload process). Output: `website/out`.

Deploy the contents of `out/` to a static host at the domain root. The host must
serve `/download/index.html` for `/download/` and use `404.html` for unknown
pages. No environment variables are required. No deployment service or domain
is presumed to exist. Root-relative asset URLs require a domain-root deployment.

`../release.json` controls the version and platform downloads. Default links
target versioned GitHub Release assets only when `published` is true. Until then,
download buttons are disabled with an availability explanation. For a self-hosted
build, set `CODEMEMORY_RELEASE_DIR` to the verified installers directory; the
builder copies those assets into `out/releases/v<version>/` and enables downloads.
See [release instructions](../docs/windows-release.md).

Future docs/changelog/releases pages can reuse the page shell in `build.mjs`.
They are intentionally not linked as nonexistent routes. The current header's
GitHub link provides source documentation and release notes.
