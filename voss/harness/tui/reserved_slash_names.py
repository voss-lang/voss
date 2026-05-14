"""Slash names owned by M8 (Project Memory).

M8 has shipped: `/save` is the memory-note handler (M8-05), `/save-session`
is the renamed snapshot handler (M8-00). The palette filter still keeps
this allow-list to document the ownership boundary — any future palette
auditor can grep these 4 names to confirm M8's slash surface.

Order is locked: see CONTEXT.md "Reserved slash command names for M8".
"""
from __future__ import annotations


RESERVED_SLASH_NAMES: tuple[str, ...] = ("/recall", "/forget", "/memory", "/save")
