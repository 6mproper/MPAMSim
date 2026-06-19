from __future__ import annotations

from collections import defaultdict
from typing import DefaultDict, Dict


class CounterBank:
    def __init__(self) -> None:
        self.requests: DefaultDict[int, int] = defaultdict(int)
        self.bytes: DefaultDict[int, int] = defaultdict(int)

    def record(self, partid: int, size_bytes: int) -> None:
        self.requests[partid] += 1
        self.bytes[partid] += size_bytes

    def snapshot(self) -> Dict[int, Dict[str, int]]:
        partids = set(self.requests) | set(self.bytes)
        return {
            partid: {"requests": self.requests[partid], "bytes": self.bytes[partid]}
            for partid in sorted(partids)
        }
