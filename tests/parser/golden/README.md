# AST Golden Snapshots

These JSON files are the canonical AST shape produced by `voss.parse(source)` for each
PRD §7 example program. They gate against parser regressions.

## Format

Each file is the result of:

```python
import json
from voss import parse, to_dict
program = parse(source, file=basename)
json.dumps(to_dict(program, normalize_spans=True), indent=2, sort_keys=False)
```

Field order matches the dataclass declaration order in `voss/ast_nodes.py`.

## Span normalization

To keep goldens robust to whitespace and formatting tweaks in the source `.voss` files,
spans are normalized in goldens:

- `span.file` -> basename only (stripped of any path prefix)
- `span.lines` -> `[0, 0]`
- `span.cols` -> `[0, 0]`
- `span.synthetic` -> preserved

Per-construct span correctness is verified separately in `tests/parser/test_spans.py`,
which reads the raw (un-normalized) AST and asserts specific line/col ranges. The golden
files exist for **structural** equality, not span equality.

## Round-trip definition

"Round-trip" in this codebase means **AST snapshot equality**:

    parse(source) -> AST -> normalized dict == golden

It does NOT mean source-byte round-trip. There is no pretty-printer in v1; reformatting
the source files would change byte output but not AST shape, and goldens stay green.

## Regenerating

If the AST shape changes intentionally (e.g. adding a new field to an existing node),
regenerate goldens with:

```bash
python -c "import json; from pathlib import Path; from voss import parse, to_dict
for n in ('classify','support','research','assistant'):
    src = Path('tests/parser/examples/'+n+'.voss').read_text()
    Path('tests/parser/golden/'+n+'.ast.json').write_text(json.dumps(to_dict(parse(src, n+'.voss'), normalize_spans=True), indent=2))"
```

Then code-review the diff to confirm only intended changes appear before committing.
