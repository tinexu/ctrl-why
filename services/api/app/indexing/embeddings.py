import hashlib
import math
import re
from dataclasses import dataclass

TOKEN_PATTERN = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


class FeatureHashEmbedder:
    """Deterministic local embeddings suitable for an ephemeral MVP index."""

    def __init__(self, dimensions: int = 256) -> None:
        if dimensions <= 0:
            raise ValueError("Embedding dimensions must be positive.")
        self.dimensions = dimensions

    def embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        for token in TOKEN_PATTERN.findall(text.lower()):
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
            value = int.from_bytes(digest, "big")
            index = value % self.dimensions
            vector[index] += -1.0 if value & 1 else 1.0
        magnitude = math.sqrt(sum(component * component for component in vector))
        return [component / magnitude for component in vector] if magnitude else vector


@dataclass(frozen=True)
class VectorEntry:
    chunk_id: str
    vector: list[float]


def cosine_similarity(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right, strict=True))

