"""Python mirror of the locked styles.tcss color palette."""
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

# tcss-var-name → value mapping consumed by the contract cross-check test
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
