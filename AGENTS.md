# Repository Guidelines

## Project Structure & Module Organization

This is a buildless, single-page chatbot exhibition for 大瓜生山祭2026, hosted on GitHub Pages. Root-level `index.html` contains the Japanese page content; `data/works.json` contains generated public work data; `script.js` loads it and renders cards and the details dialog. `scripts/import_works.py` extracts Excel submissions, keeping the latest per normalized romanized name. `scripts/capture_works.py` stages screenshots for review before copying approved images to `assets/screenshots/`. Raw XLSX files and `.local/` reports/captures are ignored. `theme.css` contains design tokens, while `styles.css` defines layout and responsive behavior. See `README.md` for editing and publishing instructions.

## Build, Test, and Development Commands

- `python3 -m http.server 8000 --bind 127.0.0.1`: serve the repository at `http://127.0.0.1:8000`.
- `node --check script.js`: verify JavaScript syntax.
- `python3 -m unittest discover -s tests`: check Excel extraction and deduplication.
- `git diff --check`: catch whitespace errors before committing.

No package installation or build step is required. GitHub Pages publishes `main` from the repository root; preserve `.nojekyll` and relative asset paths such as `./theme.css`.

## Coding Style & Naming Conventions

Use two-space indentation in HTML and JavaScript, camelCase for JavaScript functions, and kebab-case for CSS classes and custom properties. Keep work IDs unique, for example `work-01`. Adjust appearance through `theme.css` before changing component CSS. Render contributor-provided text with `textContent`. No formatter or linter is configured.

## Testing Guidelines

Python standard-library tests cover extraction; no coverage threshold is configured. Check work counts, dialog open/close, Escape, and focus restoration. Verify all imported cards at iPad sizes `1024×768` and `768×1024`, plus mobile widths `390` and `320`; confirm four iPad columns, two mobile columns, and no horizontal overflow. Keep any sample works visibly labeled and unlinked.

## Commit & Pull Request Guidelines

This is a new repository without an established commit convention. Use short, imperative subjects such as `Add chatbot exhibition site`. Keep changes focused. Pull requests should describe the result, link relevant issues, list verification performed, and include screenshots for visual changes. Updates to `main` publish automatically.

## Security & Configuration

No API keys are required. Never commit credentials, raw XLSX files, or `.local/` data. Publish student initials derived from the romanized-name column, never full names or school years. Check screenshots for names and account information before approval. Publish only public HTTPS chatbot URLs. Set `sample: false` only for actual student work.
