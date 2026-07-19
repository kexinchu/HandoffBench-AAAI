"""Dependency-free deterministic maximum-weight bipartite matching."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import TypeVar

L = TypeVar("L")
R = TypeVar("R")


def maximum_weight_pairs(
    left: Sequence[L], right: Sequence[R], weight: Callable[[L, R], float]
) -> list[tuple[int, int]]:
    """Return a one-to-one maximum-weight assignment, omitting zero edges.

    This is the O(n^3) Hungarian algorithm padded with zero-weight dummy nodes.
    Iteration order supplies deterministic tie breaking.
    """
    size = max(len(left), len(right))
    if not size:
        return []
    matrix = [
        [weight(left[i], right[j]) if i < len(left) and j < len(right) else 0.0 for j in range(size)]
        for i in range(size)
    ]
    # Standard 1-indexed Hungarian minimizer; negate weights to maximize.
    u = [0.0] * (size + 1)
    v = [0.0] * (size + 1)
    p = [0] * (size + 1)
    way = [0] * (size + 1)
    for i in range(1, size + 1):
        p[0] = i
        minv = [float("inf")] * (size + 1)
        used = [False] * (size + 1)
        j0 = 0
        while True:
            used[j0] = True
            i0 = p[j0]
            delta = float("inf")
            j1 = 0
            for j in range(1, size + 1):
                if not used[j]:
                    cur = -matrix[i0 - 1][j - 1] - u[i0] - v[j]
                    if cur < minv[j]:
                        minv[j], way[j] = cur, j0
                    if minv[j] < delta:
                        delta, j1 = minv[j], j
            for j in range(size + 1):
                if used[j]:
                    u[p[j]] += delta
                    v[j] -= delta
                else:
                    minv[j] -= delta
            j0 = j1
            if p[j0] == 0:
                break
        while True:
            j1 = way[j0]
            p[j0] = p[j1]
            j0 = j1
            if j0 == 0:
                break
    assignment = [(p[j] - 1, j - 1) for j in range(1, size + 1) if p[j]]
    return [(i, j) for i, j in assignment if i < len(left) and j < len(right) and matrix[i][j] > 0]
