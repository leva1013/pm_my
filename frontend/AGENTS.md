# Frontend AGENTS guide

## Purpose

This document describes the current frontend implementation and the rules to follow when making frontend changes.

## Current stack

- Framework: Next.js (App Router) with React and TypeScript
- Styling: Tailwind CSS v4 with CSS variables in src/app/globals.css
- Drag and drop: @dnd-kit/core and @dnd-kit/sortable
- Tests:
  - Unit/component: Vitest + Testing Library
  - End-to-end: Playwright

## Current architecture

- Entry route:
  - src/app/page.tsx renders KanbanBoard
- Global shell:
  - src/app/layout.tsx configures metadata and fonts
  - src/app/globals.css defines color tokens and shared visual variables
- Domain model and board logic:
  - src/lib/kanban.ts contains board types, seed data, id generation, and moveCard logic
- UI components:
  - src/components/KanbanBoard.tsx owns board state and drag lifecycle
  - src/components/KanbanColumn.tsx renders a single column and add-card form
  - src/components/KanbanCard.tsx renders sortable cards
  - src/components/NewCardForm.tsx handles add-card interaction
  - src/components/KanbanCardPreview.tsx renders drag overlay preview
  - src/components/AiSidebar.tsx renders the collapsible AI chat panel
  - src/components/icons.tsx holds inline SVG icons (no icon library dependency)
- Layout:
  - Full-width, viewport-height layout on lg+: compact header, columns share the
    available width (min 200px each, horizontal scroll when they do not fit), AI
    panel docked on the right and collapsible to a small rail
  - Below lg the AI panel stacks under the board; on phones columns snap-scroll

## Current behavior baseline

- Board shows five fixed columns (renamable titles).
- Cards can be created and deleted in a column.
- Cards can be reordered in-column and moved across columns.
- Initial data is currently local in-memory seed data.

## Existing test baseline

- Unit/component tests:
  - src/components/KanbanBoard.test.tsx
  - src/lib/kanban.test.ts
- End-to-end tests:
  - tests/kanban.spec.ts

## Frontend coding conventions

- Keep components simple and focused. Prefer small, explicit props.
- Keep board domain logic in src/lib when it is pure and testable.
- Keep view-state orchestration in component files, not in utility modules.
- Preserve the existing design language and color tokens from globals.css.
- Use existing typography approach from layout.tsx and CSS variables.
- Preserve accessibility basics:
  - Inputs and buttons must have clear labels or aria-label values.
  - Interactive controls must remain keyboard reachable.
- Preserve test selectors pattern:
  - Columns use data-testid="column-<id>"
  - Cards use data-testid="card-<id>"
- Add or update tests for every frontend behavior change:
  - Unit/component tests for rendering and interaction logic.
  - E2E tests for user-visible flows.
- Avoid over-engineering:
  - No new state library unless explicitly required.
  - No unnecessary abstraction layers.
- Keep API boundaries explicit when backend integration is added:
  - Isolate fetch/client code from presentational UI where practical.
- Maintain TypeScript strictness:
  - Avoid any.
  - Model payload shapes with named types.

## Frontend done criteria for future parts

A frontend task is done only when all are true:

- Lint and type checks pass.
- Relevant unit/component tests pass.
- Relevant Playwright flows pass.
- Existing behavior not targeted by change still works.
