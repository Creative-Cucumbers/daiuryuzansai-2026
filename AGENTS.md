# Repository Guidelines

## Project Structure & Module Organization

This is a buildless, single-page chatbot exhibition for 大瓜生山祭2026, hosted on GitHub Pages. Root-level `index.html` contains the Japanese page content; `data.js` defines `window.EXHIBITION_WORKS`; `script.js` renders cards, filters, and the details dialog. `theme.css` contains design tokens, while `styles.css` defines layout and responsive behavior. Static assets belong in `assets/`. See `README.md` for editing and publishing instructions.

## Build, Test, and Development Commands

- `python3 -m http.server 8000 --bind 127.0.0.1`: serve the repository at `http://127.0.0.1:8000`.
- `node --check script.js` and `node --check data.js`: verify JavaScript syntax.
- `git diff --check`: catch whitespace errors before committing.

No package installation or build step is required. GitHub Pages publishes `main` from the repository root; preserve `.nojekyll` and relative asset paths such as `./theme.css`.

## Coding Style & Naming Conventions

Use two-space indentation in HTML and JavaScript, camelCase for JavaScript functions, and kebab-case for CSS classes and custom properties. Keep work IDs unique, for example `work-01`. Adjust appearance through `theme.css` before changing component CSS. Render contributor-provided text with `textContent`. No formatter or linter is configured.

## Testing Guidelines

No automated test framework or coverage threshold is configured. Check category counts, dialog open/close, Escape, and focus restoration. Verify 20 cards at iPad sizes `1024×768` and `768×1024`, plus mobile widths `390` and `320`; confirm four iPad columns, two mobile columns, and no horizontal overflow. Keep sample works visibly labeled and unlinked.

## Commit & Pull Request Guidelines

This is a new repository without an established commit convention. Use short, imperative subjects such as `Add chatbot exhibition site`. Keep changes focused. Pull requests should describe the result, link relevant issues, list verification performed, and include screenshots for visual changes. Updates to `main` publish automatically.

## Security & Configuration

No API keys are required. Never commit credentials or local environment files. Publish only approved student names and public HTTPS chatbot URLs. Set `sample: false` only for actual student work.
