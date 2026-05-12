# Voss Demos

Language-tour demos for Voss primitives. These are repo docs, separate from the canonical `samples/` contract.

Run one demo:

```bash
voss run voss-demos/01-sentiment.voss
```

Check the full tour:

```bash
voss check voss-demos/
```

### 01-sentiment.voss - probable<T> + confidence gate

3-way enum-style classification under a confidence threshold. Below threshold emits `unsure` instead of guessing.

`voss run voss-demos/01-sentiment.voss` -> `positive (0.87)`

### 02-translate.voss - ctx budget + fallback

A scoped prompt window runs inside a stricter runtime budget. If the budget trips, the fallback returns the cheap answer.

`voss run voss-demos/02-translate.voss` -> `fallback: hola`

### 03-route.voss - match similar

Semantic routing maps user text to support lanes without keyword branching.

`voss run voss-demos/03-route.voss` -> `billing`

### 04-fact-check.voss - use + @tool

A tool declaration is available to the model context and the source imports a runtime type through `use`.

`voss run voss-demos/04-fact-check.voss` -> `stub-response`

### 05-debate.voss - spawn + gather

Two agents run concurrently and `gather` joins their replies into one line.

`voss run voss-demos/05-debate.voss` -> `stub-response | stub-response`

### 06-rag.voss - memory.semantic

A semantic memory handle retrieves one passage and feeds it into a bounded answer context.

`voss run voss-demos/06-rag.voss` -> `stub-response`
