"""Working / in-context memory assembly under a token budget."""

from __future__ import annotations

from aih.memory.models import AssembledContext, ContextFragment, RecallResult


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


class ContextAssembler:
    """Assembles ephemeral working memory from recalled fragments."""

    def build(
        self,
        goal: str,
        budget: int,
        candidates: list[RecallResult],
        *,
        scratchpad: list[str] | None = None,
    ) -> AssembledContext:
        fragments: list[ContextFragment] = []
        for r in candidates:
            fragments.append(
                ContextFragment(
                    type=r.type,
                    text=r.text,
                    provenance=r.source or r.id,
                    tokens=_estimate_tokens(r.text),
                )
            )
        for note in scratchpad or []:
            fragments.append(
                ContextFragment(
                    type="working",
                    text=note,
                    provenance="scratchpad",
                    tokens=_estimate_tokens(note),
                )
            )

        # Highest salience/score first; evict scratchpad then lowest-score when over budget.
        fragments.sort(key=lambda f: (f.type == "working", -_score_for(f, candidates)), reverse=False)
        evicted = 0
        total = sum(f.tokens for f in fragments)
        while total > budget and fragments:
            drop = fragments.pop()  # lowest priority at end after sort
            total -= drop.tokens
            evicted += 1

        return AssembledContext(
            goal=goal,
            fragments=fragments,
            total_tokens=total,
            budget=budget,
            evicted=evicted,
        )


def _score_for(fragment: ContextFragment, candidates: list[RecallResult]) -> float:
    for c in candidates:
        if c.id in fragment.provenance or c.source == fragment.provenance:
            return c.score
    return 0.5
