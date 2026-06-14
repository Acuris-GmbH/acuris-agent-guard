"""The decision layer: turn an Acuris storefront-verify response into a single
agent-actionable verdict (PROCEED / ABORT / REVIEW).

The decision is derived from the *structured boolean signals* the API returns
(`domain_bound`, `entity_resolves`, `layers.compliance.sanctions_hit`,
`layers.coherence.reachable`, ...), NOT from the API's free-form `verdict`
string — so this stays stable across API versions and is honest about the
"couldn't reach the site" case instead of guessing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

PROCEED = "PROCEED"
ABORT = "ABORT"
REVIEW = "REVIEW"


@dataclass
class StorefrontVerdict:
    domain: str
    entity_name: Optional[str]
    decision: str                 # PROCEED | ABORT | REVIEW
    reason: str                   # human + agent readable, one line
    domain_bound: Optional[bool]
    entity_resolves: Optional[bool]
    sanctions_hit: bool
    jurisdiction_risk_band: Optional[str]
    score: Optional[float]
    raw: dict = field(default_factory=dict, repr=False)

    @property
    def safe_to_pay(self) -> bool:
        return self.decision == PROCEED

    def to_dict(self) -> dict:
        return {
            "domain": self.domain,
            "entity_name": self.entity_name,
            "decision": self.decision,
            "reason": self.reason,
            "signals": {
                "domain_bound": self.domain_bound,
                "entity_resolves": self.entity_resolves,
                "sanctions_hit": self.sanctions_hit,
                "jurisdiction_risk_band": self.jurisdiction_risk_band,
            },
            "score": self.score,
        }


def decide(raw: dict) -> StorefrontVerdict:
    """Map an Acuris /storefront-verify response → StorefrontVerdict."""
    layers = raw.get("layers") or {}
    coh = layers.get("coherence") or {}
    comp = layers.get("compliance") or {}

    domain_bound = raw.get("domain_bound")
    entity_resolves = raw.get("entity_resolves")
    reachable = coh.get("reachable", True)
    sanctions = bool(comp.get("sanctions_hit") or comp.get("ubo_sanctions_hit"))
    risk_band = raw.get("jurisdiction_risk_band") or (raw.get("jurisdiction_risk") or {}).get("risk_band")
    entity_name = raw.get("bound_entity") or raw.get("register_name")

    # Order matters: hardest red flags first.
    if sanctions:
        decision, reason = ABORT, "Merchant or a beneficial owner is on a sanctions list."
    elif entity_resolves is False:
        decision, reason = ABORT, "No real registered company exists behind this storefront."
    elif domain_bound is False and reachable:
        decision, reason = (
            ABORT,
            "This domain is NOT bound to the registered company it claims to be — likely a clone.",
        )
    elif reachable is False:
        decision, reason = (
            REVIEW,
            "Storefront could not be reached to confirm the domain belongs to the entity — verify before paying.",
        )
    elif str(comp.get("default_action") or "").lower() == "block":
        decision, reason = ABORT, "Compliance policy blocks payment to this storefront."
    elif domain_bound and (entity_resolves is not False):
        decision, reason = (
            PROCEED,
            "Storefront is bound to a real, sanctions-clean registered entity.",
        )
    else:
        decision, reason = REVIEW, "Insufficient signal to confirm the storefront — verify before paying."

    return StorefrontVerdict(
        domain=raw.get("domain") or "",
        entity_name=entity_name,
        decision=decision,
        reason=reason,
        domain_bound=domain_bound,
        entity_resolves=entity_resolves,
        sanctions_hit=sanctions,
        jurisdiction_risk_band=risk_band,
        score=raw.get("score"),
        raw=raw,
    )
