"""X marks: the two diagonals of one box mark a void or a shaft (docs/rooms/DESIGN.md R-4.3). Owner: R1.

THE TRACER of the rooms scaffold R0 (see network.py) reads none: the function is here so that the pass that cuts the
slab has its call. R1 writes the rule (pairs of straight lines that are the two diagonals of one box, on every layer
except furniture, grid and dimension layers; `ignore` layers are read too).
"""
from __future__ import annotations


def x_marks(fb, net, X) -> list:
    """The floor's X marks -> [{ 'poly': the box, 'area': m2, 'what': 'void' | 'shaft' }]. The tracer finds none."""
    return []
