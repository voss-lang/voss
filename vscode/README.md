# Voss for VS Code / Cursor

Syntax highlighting + file icons for the Voss programming language (`.voss`).

## Features

- TextMate grammar (`source.voss`) covering: `fn`, `agent`, `prompt`, `class`, `let`, `match`/`case`, `ctx`, `within budget`, `try`/`catch`, `spawn`, `gather`, confidence gate (`@ p >= 0.80`), agent options (`system`, `tools`, `model`, `retries`, `memory`), durations (`60s`, `500ms`), token budgets (`2000 tokens`).
- Comment toggle (`#`), bracket matching, auto-close, indentation rules.
- Light + dark file icons in the explorer.

## Develop locally

```bash
cd vscode
# Open in a fresh VS Code window with the extension loaded:
code --extensionDevelopmentPath="$PWD" ../samples/classify.voss
```

In Cursor, replace `code` with `cursor`. Edit grammar/config and reload (`Cmd+R`) to see changes.

## Package + install

```bash
npm i -g @vscode/vsce
vsce package          # produces voss-0.0.1.vsix
code --install-extension voss-0.0.1.vsix
# Cursor:
cursor --install-extension voss-0.0.1.vsix
```

## Publish

- Marketplace (VS Code): `vsce publish` — needs an Azure DevOps PAT under publisher `voss-lang`.
- Open VSX (Cursor + others): `npx ovsx publish voss-0.0.1.vsix -p $OVSX_TOKEN`.

## Grammar reuse for github-linguist

The `syntaxes/voss.tmLanguage.json` file uses scope `source.voss` and is the same artifact a future `github-linguist` PR will vendor under `vendor/grammars/voss/`. Keep grammar fixes here as the source of truth.
