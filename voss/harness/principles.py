"""Engineering principles config substrate (V2 VPRIN-01/03/05/06).

A frozen, immutable, ordered set of engineering principles — the six shipped
defaults, optionally extended/overridden/disabled by a project-local
`.voss/principles.yml`. Mirrors the `TeamConfig` frozen-config + loud-error
(`VossTeamConfigError`) precedent in `team.py`, and the `.voss/*.yml`
`yaml.safe_load` pattern in `consensus.py` — but, deliberately unlike
`load_constraints`, this loader RAISES on malformed input (D-02) rather than
silently falling back to defaults.

Principle text is strictly OPAQUE: no code in this module branches on any
individual principle key or string — the merge is key-agnostic set algebra
(guard-tested in V2-03).
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

# D-02: the six shipped defaults live here as the single source of truth (no
# shipped .voss/principles.default.yml file). Ordered — order is stable for
# injection (V2-02) and `voss principles show` (V2-03).
DEFAULT_PRINCIPLES: tuple[tuple[str, str], ...] = (
    ("diff", "Make the smallest diff that solves the task."),
    ("evidence", "No factual claim without evidence."),
    ("tests", "Tests prove behavior, not coverage theater."),
    ("scope", "Do not edit outside assigned scope."),
    ("review", "Review intent and correctness before style."),
    ("reversibility", "Prefer reversible changes unless the user approves risk."),
)


class VossPrinciplesConfigError(Exception):
    """Raised on a malformed `.voss/principles.yml` (clear, non-silent — D-02)."""


@dataclass(frozen=True, slots=True)
class PrinciplesConfig:
    """Immutable ordered set of active principles as (key, text) pairs."""

    principles: tuple[tuple[str, str], ...]

    def as_mapping(self) -> dict[str, str]:
        return dict(self.principles)

    def keys(self) -> list[str]:
        return [k for k, _ in self.principles]

    def __iter__(self):
        return iter(self.principles)

    def __len__(self) -> int:
        return len(self.principles)


@dataclass(frozen=True, slots=True)
class _ProjectLayer:
    """Parsed project file: (key, text|None) items + explicit disable list.

    A `None` text marks a null-value disable; `disable` holds the top-level
    `disable: [keys]` list. Both remove a default (D-04).
    """

    items: tuple[tuple[str, str | None], ...]
    disable: tuple[str, ...]


def load_principles(cwd: Path) -> _ProjectLayer:
    """Read `cwd/.voss/principles.yml` into a project layer.

    Missing file → empty layer (defaults applied by merge). Present file is
    parsed with `yaml.safe_load`; the top level MUST be a mapping. A top-level
    `disable: [keys]` list is extracted; every other `key: "string"` (or
    `key: null`) becomes a project item. RAISES `VossPrinciplesConfigError` on
    invalid YAML, a non-mapping top level, a non-string/non-null value, or a
    `disable` that is not a list of strings.
    """
    path = cwd / ".voss" / "principles.yml"
    if not path.exists():
        return _ProjectLayer((), ())
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        raise VossPrinciplesConfigError(f"principles.yml: invalid YAML: {e}") from e
    if raw is None:
        return _ProjectLayer((), ())
    if not isinstance(raw, dict):
        raise VossPrinciplesConfigError(
            "principles.yml: top level must be a mapping of key: \"string\""
        )

    disable: list[str] = []
    if "disable" in raw:
        disable_raw = raw["disable"]
        if not isinstance(disable_raw, list) or not all(
            isinstance(x, str) for x in disable_raw
        ):
            raise VossPrinciplesConfigError(
                "principles.yml: `disable` must be a list of strings"
            )
        disable = list(disable_raw)

    items: list[tuple[str, str | None]] = []
    for key, value in raw.items():
        if key == "disable":
            continue
        if value is None:
            items.append((str(key), None))
            continue
        if not isinstance(value, str):
            raise VossPrinciplesConfigError(
                f"principles.yml: value for {key!r} must be a string or null"
            )
        items.append((str(key), value))
    return _ProjectLayer(tuple(items), tuple(disable))


def _resolve(
    defaults: tuple[tuple[str, str], ...],
    layer: _ProjectLayer,
) -> list[tuple[str, str, str]]:
    """Merge defaults + project layer into ordered (key, text, source) triples.

    D-04: project key not in defaults ADDS (appended after defaults in project
    order); project key matching a default REPLACES its text in place (stable
    ordinal); a default is REMOVED only when explicitly disabled (null value OR
    in the `disable` list). Conflict rule (D-04, locked): an explicit disable
    WINS over a redefinition — a key both disabled and given a value is removed.
    Key-agnostic: never branches on a specific principle key or text.
    """
    project = dict(layer.items)  # key -> text | None
    disabled = set(layer.disable) | {k for k, v in layer.items if v is None}

    out: list[tuple[str, str, str]] = []
    seen: set[str] = set()
    for key, text in defaults:
        seen.add(key)
        if key in disabled:
            continue
        if project.get(key) is not None:
            out.append((key, project[key], "project"))  # type: ignore[arg-type]
        else:
            out.append((key, text, "default"))
    for key, value in layer.items:
        if key in seen or key in disabled or value is None:
            continue
        seen.add(key)
        out.append((key, value, "project"))
    return out


def merge_principles(
    defaults: tuple[tuple[str, str], ...],
    layer: _ProjectLayer,
) -> PrinciplesConfig:
    """Active PrinciplesConfig from defaults + project layer (D-04)."""
    return PrinciplesConfig(tuple((k, t) for k, t, _ in _resolve(defaults, layer)))


def resolve_principles(cwd: Path) -> PrinciplesConfig:
    """Load the project file and merge onto the six defaults."""
    return merge_principles(DEFAULT_PRINCIPLES, load_principles(cwd))


def resolve_with_sources(cwd: Path) -> tuple[tuple[str, str, str], ...]:
    """Active principles as (key, text, source) triples for `voss principles
    show` (D-06). source ∈ {"default", "project"}."""
    return tuple(_resolve(DEFAULT_PRINCIPLES, load_principles(cwd)))
