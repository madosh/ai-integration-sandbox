"""Score fusion: weighted alpha fusion and Reciprocal Rank Fusion (RRF).

When does each win?
- **Alpha fusion** blends *magnitudes* of normalized scores. It shines when both
  signals are well-calibrated and you want to tune their relative influence.
- **RRF** blends *ranks*, ignoring score magnitudes. It is robust when the two
  signals live on incomparable scales (BM25 vs cosine), which is the common case.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class FusedScore:
    """A fused score for one item, retaining its component contributions."""

    index: int
    fused: float
    sparse: float
    dense: float
    signals: list[str]


def _min_max(scores: list[float]) -> list[float]:
    if not scores:
        return []
    lo, hi = min(scores), max(scores)
    if hi - lo < 1e-12:
        # All equal: contribute nothing distinguishing (flat 0).
        return [0.0 for _ in scores]
    return [(s - lo) / (hi - lo) for s in scores]


def alpha_fusion(sparse: list[float], dense: list[float], *, alpha: float) -> list[FusedScore]:
    """Weighted fusion over min-max-normalized scores.

    ``fused = alpha * dense_norm + (1 - alpha) * sparse_norm``. alpha=0 -> pure
    sparse, alpha=1 -> pure dense.
    """
    if not 0.0 <= alpha <= 1.0:
        raise ValueError("alpha must be in [0, 1]")
    n = len(sparse)
    if len(dense) != n:
        raise ValueError("sparse and dense score lists must be the same length")
    s_norm = _min_max(sparse)
    d_norm = _min_max(dense)
    out: list[FusedScore] = []
    for i in range(n):
        fused = alpha * d_norm[i] + (1 - alpha) * s_norm[i]
        out.append(
            FusedScore(
                index=i,
                fused=fused,
                sparse=sparse[i],
                dense=dense[i],
                signals=_contributing(s_norm[i], d_norm[i]),
            )
        )
    return out


def reciprocal_rank_fusion(
    sparse: list[float], dense: list[float], *, k: int = 60
) -> list[FusedScore]:
    """RRF over the two rankings. ``score = sum 1 / (k + rank)`` (rank is 1-indexed)."""
    n = len(sparse)
    if len(dense) != n:
        raise ValueError("sparse and dense score lists must be the same length")
    sparse_rank = _ranks(sparse)
    dense_rank = _ranks(dense)
    out: list[FusedScore] = []
    for i in range(n):
        fused = 1.0 / (k + sparse_rank[i]) + 1.0 / (k + dense_rank[i])
        out.append(
            FusedScore(
                index=i,
                fused=fused,
                sparse=sparse[i],
                dense=dense[i],
                signals=_contributing(sparse[i], dense[i]),
            )
        )
    return out


def _ranks(scores: list[float]) -> list[int]:
    """Return the 1-indexed rank of each item (1 = highest score)."""
    order = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
    ranks = [0] * len(scores)
    for rank, idx in enumerate(order, start=1):
        ranks[idx] = rank
    return ranks


def _contributing(sparse_val: float, dense_val: float, *, eps: float = 1e-9) -> list[str]:
    signals: list[str] = []
    if sparse_val > eps:
        signals.append("bm25")
    if dense_val > eps:
        signals.append("dense")
    return signals
