# Chunking Algorithm

The chunking algorithm turns markdown into recall units that preserve local meaning for embedding search. Each chunk records a source boundary, line range, and excerpt so a result can explain which heading produced the match.

## ATX Headings

ATX heading markers define normal chunk boundaries. A parser should split on markdown headings, keep the heading text with its body, and ignore heading-like text inside fenced code so code examples do not create false sections.

```python
# comment line that must stay inside the code fence
print("not a markdown heading")
```

## Oversize Guard

The oversize guard protects embedding calls from very large markdown sections while preserving a stable boundary strategy. When a section grows beyond the target chunk size, the implementation should split the body into smaller recall units without losing the original heading context, because a user query about chunk behavior should still find the explanation rather than a detached fragment. This fixture paragraph intentionally exceeds eight hundred characters so tests can exercise subsplitting. It repeats the discriminating vocabulary in a natural way: chunk selection depends on a heading boundary, the boundary keeps adjacent sentences together, and embedding quality improves when every chunk contains enough context to stand alone. The guard should not split in the middle of a short sentence when a cleaner sentence edge is available, but it may fall back to a character window for pathological input. Stable line ranges matter for golden assertions, deterministic manifests, and readable recall output. The section also mentions markdown headings, source files, local cache rebuilds, and repeatable query scoring so the fixture remains useful for both semantic and BM25 tests across environments.
