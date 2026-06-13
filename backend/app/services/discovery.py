"""Agent discovery engine - skill matching with intelligent multi-factor ranking."""
from __future__ import annotations

from sqlalchemy.orm import Session

from ..models import Agent, AgentStatus


def _skill_match(query_skill: str, agent: Agent) -> float:
    """Return 0..1 skill relevance using exact + token overlap."""
    if not query_skill:
        return 1.0
    q = query_skill.lower().strip()
    skills = [s.lower() for s in (agent.skills or [])]
    if q in skills:
        return 1.0
    # Partial / token overlap (e.g. "market analysis" vs "market-research").
    q_tokens = set(q.replace("-", " ").replace("_", " ").split())
    best = 0.0
    for s in skills:
        s_tokens = set(s.replace("-", " ").replace("_", " ").split())
        if not s_tokens:
            continue
        overlap = len(q_tokens & s_tokens) / len(q_tokens | s_tokens)
        best = max(best, overlap)
    return best


def rank(
    db: Session,
    *,
    skill: str | None = None,
    max_price: float | None = None,
    min_reputation: float | None = None,
    max_latency_ms: int | None = None,
    available_only: bool = True,
    limit: int = 20,
) -> list[tuple[Agent, float, str]]:
    """Return ranked (agent, score, reason) tuples.

    Score blends skill relevance, reputation, price competitiveness, and
    latency so the "best agent for the job" surfaces first - not just the
    cheapest or the highest-rated.
    """
    q = db.query(Agent)
    if available_only:
        q = q.filter(Agent.status == AgentStatus.available)
    candidates = q.all()

    # Normalisation bounds for price/latency scoring.
    prices = [a.price_per_task for a in candidates] or [1.0]
    latencies = [a.avg_latency_ms for a in candidates] or [1]
    p_min, p_max = min(prices), max(prices)
    l_min, l_max = min(latencies), max(latencies)

    results: list[tuple[Agent, float, str]] = []
    for a in candidates:
        skill_score = _skill_match(skill or "", a)
        if skill and skill_score == 0.0:
            continue
        if max_price is not None and a.price_per_task > max_price:
            continue
        if min_reputation is not None and a.reputation < min_reputation:
            continue
        if max_latency_ms is not None and a.avg_latency_ms > max_latency_ms:
            continue

        rep_score = a.reputation / 100.0
        price_score = 1.0 - ((a.price_per_task - p_min) / (p_max - p_min or 1))
        latency_score = 1.0 - ((a.avg_latency_ms - l_min) / (l_max - l_min or 1))

        total = (
            skill_score * 0.40
            + rep_score * 0.30
            + price_score * 0.20
            + latency_score * 0.10
        )
        reason = (
            f"skill {skill_score:.2f} · rep {rep_score:.2f} · "
            f"price {price_score:.2f} · latency {latency_score:.2f}"
        )
        results.append((a, round(total * 100, 2), reason))

    results.sort(key=lambda r: r[1], reverse=True)
    return results[:limit]
