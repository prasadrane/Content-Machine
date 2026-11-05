# Consistent editorial UI

## Plan and ownership

Preserve one theme across all six remaining pages: warm ivory surfaces, dark
ink, restrained terracotta accents, serif page headings, and readable sans-serif
body text. Comments is retired; do not restore its navigation or functionality.

1. Coordinator: define shared tokens and component classes in `ui/src/index.css`,
   align Tailwind tokens, then migrate the app shell and shared entry/approval UI.
2. Oracle worker: migrate discovery, source controls, candidates, archive,
   interview panels and their states using the shared classes.
3. Editorial worker: migrate Council and Distribution, including previews,
   comparisons, history and modal controls.
4. Settings worker: migrate Lessons, Profile and Audio with the same page headers,
   panels, fields, actions and feedback states.
5. Coordinator: inspect integration, run frontend tests and production build,
   verify removal and navigation, and record validation limits.

Workers own separate feature directories. Only the coordinator edits shared
styles, shell, API clients and backend. Keep behavior and human approval gates
unchanged. Preserve the existing Comments-removal changes.

## Shared styling contract

- `cm-page`, `cm-page-header`, `cm-page-title`, `cm-page-description`: consistent
  width, spacing, title scale and description treatment. Use `cm-page-actions`
  for wrapping header actions.
- `cm-panel`, `cm-panel-title`, `cm-subpanel`: consistent surfaces, padding,
  borders and radii. Use grid/flex classes only for layout.
- `cm-divider` provides a top separator and consistent section padding.
  `cm-panel-header` supplies the bottom separator for card headings. Panels use
  explicit `space-y-*` or `gap-*` layout so horizontal cards do not inherit
  vertical spacing.
- `cm-label`, `cm-input`, `cm-textarea`, `cm-select`: readable named fields,
  consistent padding, outline and placeholder contrast. Monospace is reserved
  for identifiers, URLs, commands and raw structured data.
- `cm-button` plus `cm-button-primary`, `cm-button-secondary`, or
  `cm-button-quiet`: one action hierarchy. Primary actions use dark ink and ivory
  text; secondary actions use a quiet outlined surface. Use `cm-icon-button`
  with an accessible name for icon-only actions. Never use color as the sole
  meaning of a control.
- `cm-chip` / `cm-chip-active`: selectable filters and compact choices.
  Preserve native control semantics and selected state.
- `cm-badge`: metadata. `cm-status` plus `cm-status-info`, `cm-status-success`,
  `cm-status-warning`, or `cm-status-error`: readable semantic feedback.
  Badge metadata may use these same color variants without the `cm-status` base.
  Topic and platform labels stay neutral; semantic colors describe outcome or
  feedback, rather than assigning unrelated colors to content categories.
- `cm-empty`, `cm-dialog`, `cm-muted`, `cm-prose`: consistent empty panels,
  modal surfaces, supporting text and reading layouts.

Do not combine shared classes with conflicting local text size, font, background,
border, radius or action color classes. Keep local classes for layout, width,
overflow and purposeful state behavior. Avoid arbitrary 10px/11px interface text.
Use 16px body/input text and at least 14px interface labels and actions. Focus
must remain visible; retain reduced-motion and responsive behavior.

## Validation

Implemented with three feature workers and a coordinating shared-style owner.
Final integration: 132 frontend tests across 34 files passed, the production Vite
build passed, and `git diff --check` passed. The rebuilt bundle contains no
Comments feature routes or screen. All referenced `cm-*` component classes are
defined; no 10px/11px interface classes remain in the feature components.

Extend behavioral/accessibility tests before changing affected interactions.
Pure presentation changes use existing behavior tests and build verification;
do not add tests that merely repeat CSS class names.

Required: offline frontend suite, production build, diff checks and six-tab
navigation without Comments. Backend removal regression previously passed 245
tests. Extra Python checks that require unavailable approval remain unverified;
do not bypass an approval-review failure.

Token-level contrast calculations: body/canvas 17.50:1, muted/surface 4.89:1,
accent-link/canvas 5.35:1, and field-border/canvas 3.42:1. These calculations do not
constitute a complete rendered-page accessibility audit. Local browser preview
was unreachable from the sandbox; full visual, screen-reader, and zoom/reflow
verification remains outstanding.
