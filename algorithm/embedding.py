from __future__ import annotations

import hashlib
import math

from algorithm.config import EMBEDDING_DIMENSIONS


def deterministic_text_embedding(
    text: str,
    *,
    dimensions: int = EMBEDDING_DIMENSIONS,
) -> list[float]:
    normalized = " ".join(text.lower().split())
    values = []
    for index in range(dimensions):
        digest = hashlib.sha256(f"{index}:{normalized}".encode("utf-8")).digest()
        unit = int.from_bytes(digest[:8], "big") / ((1 << 64) - 1)
        values.append(unit * 2.0 - 1.0)

    length = math.sqrt(sum(value * value for value in values)) or 1.0
    return [round(value / length, 6) for value in values]
