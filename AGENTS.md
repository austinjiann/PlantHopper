# Repository Guidelines

## Project Structure & Module Organization
- `frontend/` contains the Next.js + TypeScript dashboard. Primary source lives under `frontend/app/`, shared components inside `frontend/components/`, typed definitions in `frontend/types/`, and mock data in `frontend/lib/`.
- Static styling is centralized in `frontend/app/globals.css`. Add feature-specific styles with lightweight component-scoped CSS-in-JS when possible.
- Non-frontend prototypes (e.g., `april_tag_detection.py`) stay at the repository root. Keep experimental scripts isolated from the production dashboard.

## Build, Test, and Development Commands
- `cd frontend && npm install` — install dependencies for the dashboard.
- `npm run dev` — start the local development server at `http://localhost:3000` with HMR.
- `npm run build` — create an optimized production build; run before deployments.
- `npm run lint` — execute ESLint with Next.js defaults; ensure the working tree is clean afterward.

## Coding Style & Naming Conventions
- TypeScript files use strict typing; export typed props/interfaces from `frontend/types/` when shared.
- Follow React FC patterns with PascalCase for components (e.g., `PlantCard.tsx`), camelCase for variables, kebab-case for CSS class names.
- Prefer composable components in `frontend/components/`; keep files under ~200 lines with clear sections.
- Run `npm run lint` prior to pushing. Configure IDEs to format with Prettier defaults (2-space indent) and preserve ASCII.

## Testing Guidelines
- Automated tests are not yet implemented. When adding tests, colocate Playwright or Vitest specs under `frontend/__tests__/` mirroring the component directory.
- Name test files `<Component>.test.tsx` and ensure the suite exercises critical UI states.
- Update this section once coverage requirements are defined.

## Commit & Pull Request Guidelines
- Craft commits around a single concern; use concise, imperative subject lines (e.g., `Add plant card moisture trend sparkline`).
- Reference related issues in the body when applicable and summarize testing performed.
- Pull requests should include: scope summary, screenshots or recordings for UI changes, checklist of tests run, and notes on follow-up work.
