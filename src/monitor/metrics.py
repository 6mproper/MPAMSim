from __future__ import annotations

from typing import Iterable, List


def percentile(values: Iterable[float], percentile_value: float) -> float:
    ordered: List[float] = sorted(values)
    if not ordered:
        return 0.0
    if len(ordered) == 1:
        return float(ordered[0])
    position = (len(ordered) - 1) * percentile_value / 100.0
    lower = int(position)
    upper = min(len(ordered) - 1, lower + 1)
    fraction = position - lower
    return ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction
