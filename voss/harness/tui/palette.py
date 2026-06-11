"""Python-side mirror of the styles.tcss Contract v2 palette (R5, spec §4.1).

styles.tcss is the single source of truth for the 9 locked hex values.
Rich renderables (Text style strings rendered inside Static widgets)
cannot read TCSS `$vars`, so this module mirrors them for the few
unavoidable Rich-side call sites (assistant gutter, HomeScreen logo,
StatusLine zones, DiffModal line colors).

Audit rules (tests/harness/tui/test_glyph_and_color_contract.py):
  - this is the ONLY .py file under voss/harness/tui/ allowed to contain
    hex color literals;
  - every value below must exactly match its styles.tcss declaration
    (cross-checked by test_palette_matches_tcss).
"""
from __future__ import annotations

ACCENT = "#ff5b1f"   # $accent
DIM = "#888888"      # $dim
GOOD = "#5FD75F"     # $good
WARN = "#FFD75F"     # $warn
ERROR = "#FF5F5F"    # $error
BG = "#121212"       # $bg
SURFACE = "#1c1c1c"  # $surface
RAISED = "#262626"   # $raised
TEXT = "#dadada"     # $text

# tcss-var-name → value mapping consumed by the contract cross-check test.
TCSS_VARS = {
    "accent": ACCENT,
    "dim": DIM,
    "good": GOOD,
    "warn": WARN,
    "error": ERROR,
    "bg": BG,
    "surface": SURFACE,
    "raised": RAISED,
    "text": TEXT,
}
