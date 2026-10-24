# Recording checklist

## Before recording

- [ ] Restore Python 3.12 in a new `.venv-demo`; leave broken `.venv` untouched.
- [ ] Run only against `demo-preparation/recording-data` and `recording-knowledge` or new isolated equivalents.
- [ ] Confirm folders contain only synthetic seed; do not use `data/`, `knowledge/`, `.env`, or personal exports.
- [ ] Start API first at `127.0.0.1:8001`; verify `/api/v1/health` reports storage healthy.
- [ ] Start Next second at `127.0.0.1:3000`; verify its API origin.
- [ ] Confirm positive counts, problem details, and submissions; verify records match.
- [ ] Confirm submissions no longer crashes and all insight cards avoid 404.
- [ ] Resolve typecheck/lint failures; ensure no Next overlay/hydration error.
- [ ] Keep LeetCode disconnected; no credentials or real user dataset.
- [ ] Maximize 1920×1080 if available; start at 100% zoom. If labels wrap, use 90% and inspect each page.
- [ ] Use one clean browser window with only localhost tabs. Hide terminals, editor, Explorer, taskbar previews, email, chat, and notifications.
- [ ] Enable Windows Do Not Disturb / Focus; close unrelated tabs and hide developer tools.
- [ ] Verify no dev badge/error overlay. Use a clean browser profile if available; prevent password manager popups/autofill.
- [ ] Keep API/frontend terminals separate and out of the recording. Never display `.env` or raw environment listings.

## During recording

- [ ] Follow `05_FULL_DEMO_RECORDING_SCRIPT.md`; record segments as separate takes.
- [ ] Wait until each page settles; do not narrate loading skeletons as success.
- [ ] Move pointer deliberately; keep it away from key labels/code unless explaining them.
- [ ] Identify synthetic and illustrative data when shown.
- [ ] Verify each result in the UI before making a claim.
- [ ] Do not connect LeetCode, change settings, import, mark reviewed, or invoke destructive actions unless separately tested in the isolated profile.
- [ ] If an endpoint fails, stop; do not hide failure with mocked content or a fabricated response.

## Recovery and after recording

- [ ] On API error, stop; check API terminal and health, then retry once. On stale counts, verify both services use same isolated DB; never reset repo data.
- [ ] On browser error overlay/submissions crash, stop and postpone the segment until fixed and retested.
- [ ] Use cuts only between completed segments; never edit an error into success.
- [ ] Keep originals until review. Check final video for secrets, usernames, personal data, paths, notifications, and debug output.
- [ ] Preserve synthetic folders for replay. Stop frontend and API with `Ctrl+C` in each terminal.
