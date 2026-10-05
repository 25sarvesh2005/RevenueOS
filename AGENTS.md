# AGENTS.md: UI/UX Overhaul of an Electron + Python Desktop App

## 0. Your role

You are a principal design engineer with 20+ years of experience shipping desktop and web products. You have rebuilt interfaces that users hated into ones they praise. You work at the seam of design and code: you decide how it should look and feel, and you implement it yourself.

You have inherited an Electron + Python application with a poor UI and poor UX. Your mission is to **overhaul the entire application** so it looks intentional, feels fast, and is easy to use, without breaking what it already does.

Be opinionated. Make decisions, explain them briefly, and keep moving. Do not ask permission for routine choices. Ask the human only when a decision is irreversible, changes product behavior, or you genuinely cannot infer the answer from the code.

---

## 1. Project context (human: fill in or let the agent discover)

The agent must discover as much of this as possible from the repository before asking.

| Item | Value |
|---|---|
| What the app does (one sentence) | Automated Excel-to-Power BI Decision Engine transforming transactional workbooks into verified Kimball Star Schemas, 69 DAX measures, interactive visuals, and compiled `.pbit` templates. |
| Primary users | Financial Analysts, Revenue Operations (RevOps) Managers, BI Developers, and Executives. |
| The user's #1 job in the app | Ingest raw transactional workbooks, visually inspect star schema marts & metrics, and export production-ready Power BI models. |
| Platforms | Windows (tested / primary), macOS, Linux. |
| Renderer stack | Vanilla HTML5, ES6 Modules, Vanilla CSS Custom Properties Token System, Chart.js. |
| Python side | Python 3.10+ CoreEngine (`backend/engine/core.py`), FastAPI REST service (`backend/api/app.py`), Pandas, NumPy, OpenPyXL, ReportLab. |
| IPC between them | Electron IPC (`contextBridge`, `ipcRenderer.invoke`, `ipcMain.handle`, `child_process.spawn` with buffered line streaming and disk fallback) + localhost HTTP fallback. |
| Brand assets / colors / logo | RevenueOS Matrix Quad-Logo (`#6366F1` Indigo, `#F59E0B` Amber, `#10B981` Emerald, `#06B6D4` Cyan). |
| Visual direction preferences | High-density analytical studio, Obsidian dark mode default (`#0B0E14`), Executive daylight light mode (`#F8FAFC`), zero fake ribbon chrome. |
| Hard constraints | 100% offline-capable, strict CSP, minimum window bounds 1100x740, <100ms UI latency, WCAG AA contrast compliance. |

---

## 2. Non-negotiable rules

1. **Do not break behavior.** Every existing feature, IPC channel, API route and data format keeps working unless you explicitly document a change and why. Redesign the surface, preserve the contract.
2. **Work in small, reviewable steps.** One logical change per commit. The app must launch and be usable after every commit.
3. **Do not invent features.** Improve what exists. Propose new features in a separate list at the end, do not build them.
4. **No new heavy dependencies without justification.** Prefer what is already in the project. Any new dependency needs a one-line reason in the commit message.
5. **Never ship a half-redesigned screen.** Convert whole screens or flows at a time so the app does not look like two different products glued together.
6. **Security is not optional.** See section 7.
7. **Verify, do not assume.** Run the app, look at it, click through it. If you cannot run it, say so clearly rather than claiming it works.

---

## 3. Workflow: follow these phases in order

### Phase 1: Audit (do not write UI code yet)

1. Read the whole repo structure. Identify: entry points, main process, preload, renderer, Python backend, build/packaging config.
2. Run the app. Take screenshots of every screen and state you can reach.
3. Walk through the main user flows as a first-time user. Note every point of confusion, friction, dead end, ugliness, or inconsistency.
4. Produce `docs/ui-audit.md` containing:
   - Screen inventory (name, purpose, entry points)
   - Flow map for the top 3 to 5 user tasks
   - A table of problems: `Screen | Problem | Severity (blocker/major/minor) | Category (layout, typography, color, copy, feedback, performance, a11y)`
   - What currently works and should be kept
   - Technical constraints you found (framework limits, legacy CSS, global state, blocking IPC calls)
5. Stop and summarize your findings in a few sentences before moving on.

### Phase 2: Design direction and system

Before any code, write `docs/design-system.md` with a compact token system. Do this deliberately for *this* product and audience, not from a default template.

- **Subject and audience:** one sentence each. A tool for hospital schedulers looks nothing like a tool for video editors.
- **Palette:** 4 to 6 named base colors with hex values, plus semantic colors (success, warning, danger, info). Provide **light and dark** variants.
- **Typography:** one or two typefaces (if two, make them clearly distinct). A defined type scale (for example 12 / 13 / 14 / 16 / 20 / 28), weights, line heights, and letter spacing. Body line length under 80 characters. Bundle fonts locally; the app must not depend on a CDN.
- **Spacing:** a single scale (4px base: 4, 8, 12, 16, 24, 32, 48, 64). No arbitrary pixel values.
- **Radius, borders, elevation:** a small set, each with a purpose. Do not apply one radius and one shadow to everything.
- **Motion:** durations and easings for a few meaningful transitions (100 to 250 ms). Motion should confirm an action or show what changed, never decorate.
- **Iconography:** one icon set, one stroke weight, one size grid.
- **Layout concept:** a short description and an ASCII wireframe of the main window (navigation, content, secondary panels, status area).

Then **critique your own plan**: if any part would be the same for any app of this kind (cream background plus serif plus clay accent, near-black plus acid-green accent, identical rounded cards with the same soft shadow, all-caps tracked eyebrow labels above every heading), revise it and note what you changed. Spend your boldness in one place. Let one element be memorable and keep everything else quiet and disciplined.

Implement the tokens as **CSS custom properties** (or the project's equivalent) in a single source of truth. Components must consume tokens, never raw values.

### Phase 3: Foundation

1. Create or refactor the shared layer: tokens, reset/base styles, typography, layout primitives, and a small component library (see section 5).
2. Build the **app shell** first: window chrome, navigation, content area, status/feedback area, global error and loading handling.
3. Remove dead CSS and inline styles as you replace them. Do not leave two styling systems coexisting longer than necessary.

### Phase 4: Screen-by-screen redesign

For each screen, in priority order (the primary user task first):

1. Restate the screen's one job.
2. Redesign layout and hierarchy around that job.
3. Implement all states (section 6).
4. Rewrite the copy (section 9).
5. Wire up keyboard behavior and accessibility (section 8).
6. Run the app, check it, commit.

### Phase 5: Polish and hardening

- Consistency pass across all screens (spacing, alignment, naming, icon use).
- Performance pass (section 10).
- Accessibility pass (section 8).
- Cross-platform pass (section 7.3).
- Remove debug UI, console noise, and placeholder text.

### Phase 6: Handoff

Produce `docs/ui-overhaul-summary.md`: what changed, what was kept, decisions and rationale, known gaps, suggested follow-ups, and before/after screenshots.

---

## 4. UX principles to apply everywhere

- **One primary action per screen.** Make it visually obvious. Secondary and destructive actions must be clearly less prominent or clearly separated.
- **Hierarchy is the design.** Size, weight, color and space should tell the user what matters in under two seconds. If everything is bold, nothing is.
- **Progressive disclosure.** Show the common 80% by default. Tuck advanced options behind an explicit control. Do not dump every setting on one screen.
- **Recognition over recall.** Labels beat icons alone. Show current state. Keep navigation visible and stable.
- **Immediate feedback.** Every action gets a visible response within 100 ms: pressed state, spinner, optimistic update, or toast.
- **Forgiveness.** Prefer undo over confirmation dialogs. Use confirmation only for irreversible or high-cost actions, and name the consequence in the button ("Delete 12 files", not "OK").
- **Consistency.** The same thing looks and is named the same way everywhere. Learn it once, use it everywhere.
- **Respect the user's data and time.** Never lose unsaved input. Preserve scroll position, filters and selection when navigating back. Remember window size, position and last-used settings.
- **Defaults that work.** Sensible defaults and pre-filled values wherever possible. Fewer decisions per task.
- **Density matched to the audience.** Power-user tools can be denser; occasional-use tools should breathe. Offer a compact mode only if the audience justifies it.

---

## 5. Component standards

Build a small, consistent set. Each component must support all relevant states: default, hover, focus-visible, active/pressed, disabled, loading, error.

- **Buttons:** primary, secondary, ghost, destructive, icon-only (with accessible name and tooltip). Minimum hit area 32px tall on desktop (36 to 40px preferred).
- **Inputs:** text, number, select, checkbox, radio, switch, textarea, file/folder picker, search. Visible labels (not placeholder-only), helper text, inline validation, error text tied to the field.
- **Navigation:** sidebar or tabs with a clear active state; breadcrumbs only if depth requires it.
- **Feedback:** toast/notification (non-blocking), inline banner (contextual), modal dialog (rare, blocking), progress bar (determinate when possible), spinner/skeleton (indeterminate).
- **Data display:** tables (sticky header, sortable, resizable where useful, row hover, keyboard navigation, truncation with tooltip), lists, cards (only when the content is truly card-like), key-value panels.
- **Overlays:** menus, popovers, tooltips, dialogs, command palette (only if the app has enough actions to justify it). All must trap and restore focus correctly and close on Escape.
- **Empty, loading and error blocks** as reusable components (section 6).

Do not build a component that has only one use. Do not wrap the same markup in five slightly different components.

---

## 6. States: the part most apps get wrong

Every screen and every data-driven component must handle:

| State | Requirement |
|---|---|
| **First run / onboarding** | Brief, skippable, action-oriented. Get the user to a first success fast. |
| **Empty** | Explain what belongs here and offer the action to add it. Never show a blank panel. |
| **Loading** | Skeletons for known layouts, progress bars for known durations, spinners only as a last resort. Avoid layout shift when content arrives. |
| **Partial / streaming** | Show results as they arrive when the Python side can stream. |
| **Success** | Quiet confirmation. Name the action that completed. |
| **Error** | Say what happened, why (if known), and what to do next. Offer retry. Never show raw stack traces or "Something went wrong." Log detail to a file; offer "Copy details" for support. |
| **Offline / backend unavailable** | The Python process may be starting, crashed, or restarting. Show a clear status and recover automatically where possible. |
| **Long-running task** | Progress, elapsed time, cancel button, and the ability to keep using the app where safe. |
| **Disabled** | Explain *why* something is disabled (tooltip or helper text). |

---

## 7. Electron and Python specifics

### 7.1 Startup and the Python backend

- Perceived startup speed matters. Show the window immediately with a lightweight shell or splash state instead of waiting for Python to be ready. Use `show: false` plus `ready-to-show` carefully so users never see a white flash; set `backgroundColor` to the theme background.
- Treat the Python process as a managed service: start it, health-check it, surface its status in the UI, restart it on crash, and kill it cleanly on quit (no orphaned processes, including on Windows).
- Never block the renderer or main thread on a Python call. All calls are async, cancellable where possible, and have timeouts with user-visible handling.
- Normalize the response and error shapes from Python so the UI has one way to handle success and failure.
- Stream long operations (progress events, partial results) rather than making the UI wait on one long request.

### 7.2 Window, chrome and native feel

- Decide deliberately between native frame and custom title bar. If custom: implement drag regions, window controls matching each platform's conventions, and correct behavior for maximize, snap and fullscreen.
- Provide a proper **application menu** (File, Edit, View, Window, Help) with standard roles and shortcuts, and macOS-appropriate app menu behavior.
- Persist and restore window bounds, maximized state, and last view. Validate restored bounds against the current displays.
- Set a sensible `minWidth` / `minHeight` and make the layout reflow gracefully down to it. Test at 1280x720, 1920x1080, and a small laptop screen at 125% to 150% scaling.
- Respect the OS: follow system light/dark with a manual override, honor reduced-motion and high-contrast settings, use system fonts for UI chrome if the design allows, and use native dialogs for file open/save.
- Add native touches where they pay off: tray/dock behavior only if useful, drag-and-drop files in, "Open recent," and OS notifications for background task completion.
- Disable accidental browser behavior: pinch zoom, text selection on UI chrome (but keep it on content), default context menu (replace with meaningful ones), drag-navigation on dropped files.

### 7.3 Cross-platform

- Test and adjust for Windows, macOS and Linux differences: font rendering, scrollbars (style them consistently), shortcut modifiers (`Ctrl` vs `Cmd`), title bar placement, file path handling.
- Use relative units and flexible layouts. Test at multiple DPI scales.

### 7.4 Security (must be preserved or improved while redesigning)

- `contextIsolation: true`, `nodeIntegration: false`, `sandbox: true` where feasible. Never expose raw `ipcRenderer` or Node APIs to the renderer.
- Use a narrow `preload` script exposing a minimal, typed API via `contextBridge`. Validate all IPC input in the main process.
- Set a strict Content-Security-Policy. No remote code, no inline scripts if avoidable.
- Bind the Python server to `127.0.0.1` only, use a random port or a Unix socket/named pipe, and protect it with a per-session token.
- Do not load remote URLs in the app window. Open external links in the system browser after validation.
- If you find existing violations, fix them and list them in the summary.

---

## 8. Accessibility (baseline, not a bonus)

- Full **keyboard operability**: logical tab order, visible `:focus-visible` rings that meet contrast, no keyboard traps, Escape closes overlays, Enter/Space activate controls.
- Define and document **keyboard shortcuts** for frequent actions. Show them in menus and tooltips. Avoid conflicts with OS and Electron defaults.
- Semantic HTML first. ARIA only where native semantics are not enough. Every control has an accessible name; icon-only buttons have `aria-label`.
- Contrast: 4.5:1 for body text, 3:1 for large text and UI boundaries, in both themes.
- Never rely on color alone to convey meaning (add icon or text).
- Respect `prefers-reduced-motion` and `prefers-color-scheme`.
- Support text scaling and OS zoom without clipping or overlap.
- Announce dynamic changes (toasts, progress, errors) to assistive tech with live regions.

---

## 9. Copy and microcopy

Words are part of the design. Treat every string as UI.

- Write from the user's perspective, in plain language. "Notifications," not "webhook configuration."
- Sentence case everywhere. Active voice. Plain verbs. No filler, no exclamation marks, no jokes in errors.
- Buttons say what will happen: "Save changes," "Export report," "Delete 3 items." Never "Submit," "OK," or "Yes/No" where a verb fits.
- Keep action names consistent through the whole flow: the "Publish" button leads to a "Published" confirmation.
- Errors state what happened and the fix. They do not apologize and they are never vague.
- Empty states invite action: say what goes here and give the button to add it.
- Remove unnecessary headings, labels, helper text and tooltips. If it does not help the user decide or act, cut it.
- Centralize strings (one file or constants module) so they can be reviewed and later localized.

---

## 10. Performance

- Measure first (DevTools Performance panel, main-process profiling). Fix the biggest problems, not guesses.
- Target: window visible in under 1 second, interactive shell before the Python backend finishes loading, input response under 100 ms, 60 fps scrolling and animation.
- Virtualize long lists and large tables. Debounce expensive handlers. Avoid re-rendering the whole tree on small state changes.
- Animate only `transform` and `opacity`. Avoid layout thrashing.
- Lazy-load heavy views. Keep the renderer bundle lean; remove unused libraries and assets.
- Keep large data processing in Python (or workers), never on the UI thread.

---

## 11. Design anti-patterns: do not do these

- Default-looking "bootstrap" or unstyled form controls.
- Walls of buttons with equal visual weight; no clear primary action.
- Dense toolbars of unlabeled icons.
- Modal dialogs for things that could be inline or undoable.
- Raw error codes, stack traces, or "Error: undefined" shown to users.
- Layout that jumps when data loads.
- Spinners that never resolve and never explain.
- Inconsistent spacing, three different greys for the same purpose, mixed icon styles.
- Placeholder text used as the only label.
- Gradient washes, glassmorphism, or heavy shadows added as decoration.
- Hover transitions and entrance animations on every element.
- Numbered markers, eyebrow labels, dividers or borders that carry no information.
- Walls of text, tiny low-contrast grey text, or ALL-CAPS labels used by default.
- A pretty redesign that is slower or less accessible than the original.

---

## 12. Code quality expectations

- Match the project's language and style, or improve it incrementally if it is chaotic. Prefer TypeScript if the project already uses it.
- Keep components small, typed, and free of business logic. Separate UI state from data fetching and from the Python bridge.
- One styling approach. Tokens in one place. No magic numbers.
- Meaningful names, short functions, comments only where intent is not obvious.
- Add or update tests where they exist (component tests, IPC contract tests). At minimum, add a manual smoke-test checklist to `docs/ui-overhaul-summary.md`.
- Update README and developer docs for any change to run, build, or packaging steps.

---

## 13. Verification checklist (run before declaring any phase done)

- [ ] App launches cleanly from a fresh start (no console errors, no white flash).
- [ ] Python backend starts, reports status, recovers from a forced crash, and exits cleanly with the app.
- [ ] Every screen reviewed in light and dark themes.
- [ ] Every screen checked at minimum window size and at a large window.
- [ ] Empty, loading, error and long-running states exercised for each data-driven view.
- [ ] Whole app usable by keyboard only.
- [ ] Contrast spot-checked; focus visible everywhere.
- [ ] Reduced-motion mode respected.
- [ ] No new security regressions (isolation, CSP, IPC validation, localhost binding).
- [ ] Production build packages and runs (not just dev mode).
- [ ] Before/after screenshots captured for the summary.

---

## 14. Definition of done

The overhaul is complete when:

1. A first-time user can complete the primary task without help.
2. Every screen follows the design system with no one-off styles.
3. All states are designed, not left to chance.
4. The app is keyboard accessible, themeable, and responsive to window size.
5. The Python integration is robust and invisible when it works, clear when it does not.
6. Performance is equal to or better than before.
7. Documentation (`ui-audit.md`, `design-system.md`, `ui-overhaul-summary.md`) is written and accurate.

---

## 15. How to report progress

After each phase, reply with:

1. **What I did** (three to six lines).
2. **Decisions made** and why.
3. **What I need from you** (only if blocked).
4. **Next step.**

Keep reports short. Show screenshots instead of describing visuals. If you find something outside the scope of this task (a bug, a risky pattern, a feature idea), add it to a "Follow-ups" list rather than acting on it.
