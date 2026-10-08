"""Dependency-free BM25 retriever over markdown knowledge-base files.

Each `## Heading` section is one chunk. Swap `Retriever` for a pgvector/FAISS
implementation by keeping the same `search()` signature.
"""
import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

KB_DIR = Path(__file__).parent / "kb"
_TOKEN = re.compile(r"[a-z0-9]+")
_STOP = {"the", "a", "an", "is", "are", "of", "to", "and", "i", "my", "me", "do", "can", "how", "what", "in", "for", "on", "it", "be", "you", "we", "or", "if"}


def tokenize(text: str) -> list[str]:
    return [t for t in _TOKEN.findall(text.lower()) if t not in _STOP]


@dataclass
class Chunk:
    doc: str
    section: str
    text: str
    tokens: list[str]


@dataclass
class Hit:
    doc: str
    section: str
    text: str
    score: float


class Retriever:
    def __init__(self, kb_dir: Path = KB_DIR, k1: float = 1.5, b: float = 0.75):
        self.k1, self.b = k1, b
        self.chunks: list[Chunk] = []
        for path in sorted(kb_dir.glob("*.md")):
            for part in re.split(r"^## ", path.read_text(), flags=re.M)[1:]:
                title, _, body = part.partition("\n")
                text = body.strip()
                self.chunks.append(Chunk(path.stem, title.strip(), text, tokenize(f"{title} {title} {text}")))
        self.avg_len = sum(len(c.tokens) for c in self.chunks) / max(len(self.chunks), 1)
        df: Counter = Counter()
        for c in self.chunks:
            df.update(set(c.tokens))
        n = len(self.chunks)
        self.idf = {t: math.log(1 + (n - d + 0.5) / (d + 0.5)) for t, d in df.items()}

    def search(self, query: str, k: int = 3, min_score: float = 0.0) -> list[Hit]:
        q = tokenize(query)
        hits = []
        for c in self.chunks:
            tf = Counter(c.tokens)
            score = 0.0
            for t in q:
                if t in tf:
                    f = tf[t]
                    denom = f + self.k1 * (1 - self.b + self.b * len(c.tokens) / self.avg_len)
                    score += self.idf.get(t, 0) * f * (self.k1 + 1) / denom
            if score > min_score:
                hits.append(Hit(c.doc, c.section, c.text, round(score, 3)))
        return sorted(hits, key=lambda h: h.score, reverse=True)[:k]
